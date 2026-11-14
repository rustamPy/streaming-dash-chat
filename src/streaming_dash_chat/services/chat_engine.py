from __future__ import annotations

import time
import uuid
from typing import AsyncIterator

from streaming_dash_chat.models import (
    LogEvent,
    Message,
    Role,
    StreamChunk,
    StreamChunkType,
)
from streaming_dash_chat.providers.base import BaseChatProvider
from streaming_dash_chat.services.conversation_manager import ConversationManager
from streaming_dash_chat.services.sinks import SinkDispatcher, build_record
from streaming_dash_chat.services.stream_manager import StreamManager


class ChatEngine:
    def __init__(
        self,
        provider: BaseChatProvider,
        conversations: ConversationManager,
        streams: StreamManager,
        sinks: SinkDispatcher | None = None,
        chat_id: str = "",
    ) -> None:
        self.provider = provider
        self.conversations = conversations
        self.streams = streams
        self.sinks = sinks or SinkDispatcher()
        self.chat_id = chat_id

    def _event(self, type_: str, session_id: str, conversation_id: str, **data) -> None:
        self.sinks.emit(
            "on_event",
            LogEvent(
                type=type_,
                chat_id=self.chat_id,
                session_id=session_id,
                conversation_id=conversation_id,
                data=data,
            ),
        )

    async def stream_reply(
        self,
        session_id: str,
        conversation_id: str,
        stream_id: str,
        user_text: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        if user_text is not None:
            self.conversations.add_message(
                session_id, conversation_id, Message(role=Role.USER, content=user_text)
            )
        history = self.conversations.history(session_id, conversation_id)

        handle = self.streams.register(stream_id)
        assistant_id = uuid.uuid4().hex
        assistant_text = ""
        usage = None
        error: str | None = None
        outcome = "aborted"
        started = time.time()
        self._event(
            "stream_started",
            session_id,
            conversation_id,
            stream_id=stream_id,
            model=getattr(self.provider, "model", None),
        )
        try:
            async for chunk in self.provider.stream(history):
                if handle.cancelled:
                    error, outcome = "cancelled", "cancelled"
                    yield StreamChunk(
                        type=StreamChunkType.ERROR,
                        error="cancelled",
                        message_id=assistant_id,
                    )
                    return
                if chunk.type == StreamChunkType.TOKEN:
                    assistant_text += chunk.text
                elif chunk.type == StreamChunkType.DONE:
                    usage, outcome = chunk.usage, "done"
                    chunk = chunk.model_copy(update={"message_id": assistant_id})
                elif chunk.type == StreamChunkType.ERROR:
                    error, outcome = chunk.error, "error"
                    chunk = chunk.model_copy(update={"message_id": assistant_id})
                yield chunk
                if chunk.type in (StreamChunkType.DONE, StreamChunkType.ERROR):
                    break
        finally:
            self.streams.unregister(stream_id)
            if assistant_text:
                self.conversations.add_message(
                    session_id,
                    conversation_id,
                    Message(
                        id=assistant_id, role=Role.ASSISTANT, content=assistant_text
                    ),
                )
                self.sinks.emit(
                    "on_conversation_updated",
                    build_record(
                        self.chat_id,
                        session_id,
                        conversation_id,
                        self.conversations.history(session_id, conversation_id),
                    ),
                )
            self._event(
                "stream_finished" if outcome == "done" else "stream_error",
                session_id,
                conversation_id,
                stream_id=stream_id,
                outcome=outcome,
                error=error,
                duration_s=round(time.time() - started, 3),
                chars=len(assistant_text),
                usage=usage.model_dump() if usage else None,
            )

    def regenerate_reply(
        self, session_id: str, conversation_id: str, stream_id: str
    ) -> AsyncIterator[StreamChunk]:
        last = self.conversations.pop_last(session_id, conversation_id)
        if last is not None and last.role != Role.ASSISTANT:
            self.conversations.add_message(session_id, conversation_id, last)
        return self.stream_reply(session_id, conversation_id, stream_id, user_text=None)
