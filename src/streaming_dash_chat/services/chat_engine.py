"""Orchestrates a provider, conversation history, and stream cancellation
into a single async chunk stream consumable by the Flask SSE route."""

from __future__ import annotations

from typing import AsyncIterator

from streaming_dash_chat.models import Message, Role, StreamChunk, StreamChunkType
from streaming_dash_chat.providers.base import BaseChatProvider
from streaming_dash_chat.services.conversation_manager import ConversationManager
from streaming_dash_chat.services.stream_manager import StreamManager


class ChatEngine:
    def __init__(
        self,
        provider: BaseChatProvider,
        conversations: ConversationManager,
        streams: StreamManager,
    ) -> None:
        self.provider = provider
        self.conversations = conversations
        self.streams = streams

    async def stream_reply(
        self,
        session_id: str,
        conversation_id: str,
        stream_id: str,
        user_text: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream an assistant reply, persisting both the user turn (unless
        ``user_text`` is None, e.g. on regenerate) and the assistant turn to
        conversation history exactly once each, regardless of how the stream
        ends."""
        if user_text is not None:
            self.conversations.add_message(
                session_id, conversation_id, Message(role=Role.USER, content=user_text)
            )
        history = self.conversations.history(session_id, conversation_id)

        handle = self.streams.register(stream_id)
        assistant_text = ""
        try:
            async for chunk in self.provider.stream(history):
                if handle.cancelled:
                    yield StreamChunk(type=StreamChunkType.ERROR, error="cancelled")
                    return
                if chunk.type == StreamChunkType.TOKEN:
                    assistant_text += chunk.text
                yield chunk
                if chunk.type in (StreamChunkType.DONE, StreamChunkType.ERROR):
                    break
        finally:
            self.streams.unregister(stream_id)
            if assistant_text:
                self.conversations.add_message(
                    session_id, conversation_id, Message(role=Role.ASSISTANT, content=assistant_text)
                )

    def regenerate_reply(self, session_id: str, conversation_id: str, stream_id: str) -> AsyncIterator[StreamChunk]:
        """Drop the last assistant turn (and, if present, nothing else) and
        re-stream a fresh reply to the existing last user message."""
        last = self.conversations.pop_last(session_id, conversation_id)
        if last is not None and last.role != Role.ASSISTANT:
            # Nothing to regenerate (e.g. conversation ended on a user turn);
            # put it back untouched.
            self.conversations.add_message(session_id, conversation_id, last)
        return self.stream_reply(session_id, conversation_id, stream_id, user_text=None)
