"""Tests for the chat engine: streaming chunk handling, cancellation,
errors, history persistence, and conversation isolation across sessions."""

from __future__ import annotations

import pytest

from streaming_dash_chat.models import Role, StreamChunkType
from streaming_dash_chat.providers.mock import MockProvider
from streaming_dash_chat.services.chat_engine import ChatEngine
from streaming_dash_chat.services.conversation_manager import ConversationManager
from streaming_dash_chat.services.stream_manager import StreamManager


def make_engine(**provider_kwargs) -> ChatEngine:
    provider = MockProvider(reply="hello world", delay_seconds=0, **provider_kwargs)
    return ChatEngine(provider, ConversationManager(), StreamManager())


@pytest.mark.asyncio
async def test_stream_reply_yields_tokens_then_done_and_persists_history() -> None:
    engine = make_engine()

    chunks = [
        c async for c in engine.stream_reply("sess-1", "conv-1", "stream-1", user_text="hi")
    ]

    token_text = "".join(c.text for c in chunks if c.type == StreamChunkType.TOKEN)
    assert token_text == "hello world"
    assert chunks[-1].type == StreamChunkType.DONE

    history = engine.conversations.history("sess-1", "conv-1")
    assert [m.role for m in history] == [Role.USER, Role.ASSISTANT]
    assert history[0].content == "hi"
    assert history[1].content == "hello world"


@pytest.mark.asyncio
async def test_stream_reply_emits_error_chunk_and_still_persists_user_turn() -> None:
    engine = make_engine(fail_with="upstream exploded")

    chunks = [
        c async for c in engine.stream_reply("sess-1", "conv-1", "stream-1", user_text="hi")
    ]

    assert chunks[-1].type == StreamChunkType.ERROR
    assert chunks[-1].error == "upstream exploded"
    history = engine.conversations.history("sess-1", "conv-1")
    # The user turn is kept even though the assistant failed to reply; no
    # assistant message is added since nothing was actually generated.
    assert [m.role for m in history] == [Role.USER]


@pytest.mark.asyncio
async def test_cancel_stops_stream_before_completion() -> None:
    provider = MockProvider(reply="one two three four five", delay_seconds=0.05)
    engine = ChatEngine(provider, ConversationManager(), StreamManager())

    received = []
    agen = engine.stream_reply("sess-1", "conv-1", "stream-1", user_text="hi")
    async for chunk in agen:
        received.append(chunk)
        if len(received) == 2:
            assert engine.streams.cancel("stream-1") is True

    assert received[-1].type == StreamChunkType.ERROR
    assert received[-1].error == "cancelled"
    assert len(received) < 6  # didn't run to natural completion


@pytest.mark.asyncio
async def test_conversation_isolation_across_sessions() -> None:
    engine = make_engine()

    await _drain(engine.stream_reply("sess-A", "conv-1", "s1", user_text="from A"))
    await _drain(engine.stream_reply("sess-B", "conv-1", "s2", user_text="from B"))

    history_a = engine.conversations.history("sess-A", "conv-1")
    history_b = engine.conversations.history("sess-B", "conv-1")

    assert history_a[0].content == "from A"
    assert history_b[0].content == "from B"
    assert len(history_a) == 2 and len(history_b) == 2


@pytest.mark.asyncio
async def test_regenerate_replaces_last_assistant_turn() -> None:
    engine = make_engine()
    await _drain(engine.stream_reply("sess-1", "conv-1", "s1", user_text="hi"))
    assert len(engine.conversations.history("sess-1", "conv-1")) == 2

    await _drain(engine.regenerate_reply("sess-1", "conv-1", "s2"))

    history = engine.conversations.history("sess-1", "conv-1")
    assert [m.role for m in history] == [Role.USER, Role.ASSISTANT]
    assert history[0].content == "hi"  # user turn untouched
    assert history[1].content == "hello world"  # assistant turn regenerated


async def _drain(agen) -> None:
    async for _ in agen:
        pass
