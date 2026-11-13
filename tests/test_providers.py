"""Unit tests for provider adapters, using mocked SDK clients (no network/API key)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from streaming_dash_chat.models import Message, Role, StreamChunkType
from streaming_dash_chat.providers.openai import OpenAIProvider
from streaming_dash_chat.providers.pydantic_ai import PydanticAIProvider


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


def _delta_event(text: str | None, usage: Any = None) -> MagicMock:
    event = MagicMock()
    choice = MagicMock()
    choice.delta.content = text
    event.choices = [choice]
    event.usage = usage
    return event


class _FakeStream:
    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for event in self._events:
            yield event


@pytest.fixture
def fake_openai_client() -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_openai_stream_yields_tokens_then_done(fake_openai_client: MagicMock) -> None:
    usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    fake_openai_client.chat.completions.create.return_value = _FakeStream(
        [
            _delta_event("Hel"),
            _delta_event("lo"),
            _delta_event(None, usage=usage),
        ]
    )
    provider = OpenAIProvider(model="gpt-4.1", client=fake_openai_client)

    chunks = [c async for c in provider.stream([Message(role=Role.USER, content="hi")])]

    assert [c.text for c in chunks if c.type == StreamChunkType.TOKEN] == ["Hel", "lo"]
    assert chunks[-1].type == StreamChunkType.DONE
    assert chunks[-1].usage.total_tokens == 15

    sent_kwargs = fake_openai_client.chat.completions.create.call_args.kwargs
    assert sent_kwargs["model"] == "gpt-4.1"
    assert sent_kwargs["messages"][-1] == {"role": "user", "content": "hi"}


@pytest.mark.asyncio
async def test_openai_stream_emits_error_chunk_on_sdk_failure(fake_openai_client: MagicMock) -> None:
    fake_openai_client.chat.completions.create.side_effect = RuntimeError("boom")
    provider = OpenAIProvider(model="gpt-4.1", client=fake_openai_client)

    chunks = [c async for c in provider.stream([Message(role=Role.USER, content="hi")])]

    assert len(chunks) == 1
    assert chunks[0].type == StreamChunkType.ERROR
    assert "boom" in chunks[0].error


@pytest.mark.asyncio
async def test_openai_generate_returns_chat_response(fake_openai_client: MagicMock) -> None:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="hello there"))]
    response.usage = MagicMock(prompt_tokens=1, completion_tokens=2, total_tokens=3)
    fake_openai_client.chat.completions.create.return_value = response

    provider = OpenAIProvider(model="gpt-4.1", client=fake_openai_client)
    result = await provider.generate([Message(role=Role.USER, content="hi")])

    assert result.content == "hello there"
    assert result.usage.total_tokens == 3


def test_openai_system_prompt_is_prepended(fake_openai_client: MagicMock) -> None:
    provider = OpenAIProvider(client=fake_openai_client, system_prompt="be nice")
    formatted = provider._to_openai_messages([Message(role=Role.USER, content="hi")])
    assert formatted[0] == {"role": "system", "content": "be nice"}
    assert formatted[1] == {"role": "user", "content": "hi"}


# ---------------------------------------------------------------------------
# PydanticAIProvider
# ---------------------------------------------------------------------------


class _FakeStreamResult:
    def __init__(self, deltas: list[str], usage: Any) -> None:
        self._deltas = deltas
        self._usage = usage

    async def stream_text(self, delta: bool = True):
        for d in self._deltas:
            yield d

    def usage(self) -> Any:
        return self._usage


class _FakeRunStreamCtx:
    def __init__(self, result: _FakeStreamResult) -> None:
        self._result = result

    async def __aenter__(self) -> _FakeStreamResult:
        return self._result

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


@pytest.fixture
def fake_agent() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
async def test_pydantic_ai_stream_yields_deltas_then_done(fake_agent: MagicMock) -> None:
    usage = MagicMock(request_tokens=7, response_tokens=3, total_tokens=10)
    fake_agent.run_stream.return_value = _FakeRunStreamCtx(_FakeStreamResult(["Hi", " there"], usage))

    provider = PydanticAIProvider(agent=fake_agent)
    messages = [
        Message(role=Role.USER, content="earlier question"),
        Message(role=Role.ASSISTANT, content="earlier answer"),
        Message(role=Role.USER, content="new question"),
    ]
    chunks = [c async for c in provider.stream(messages)]

    assert [c.text for c in chunks if c.type == StreamChunkType.TOKEN] == ["Hi", " there"]
    assert chunks[-1].type == StreamChunkType.DONE
    assert chunks[-1].usage.total_tokens == 10

    call_kwargs = fake_agent.run_stream.call_args.kwargs
    assert call_kwargs["message_history"]  # prior turns were translated, not dropped


@pytest.mark.asyncio
async def test_pydantic_ai_stream_emits_error_chunk_on_failure(fake_agent: MagicMock) -> None:
    fake_agent.run_stream.side_effect = RuntimeError("agent exploded")
    provider = PydanticAIProvider(agent=fake_agent)

    chunks = [c async for c in provider.stream([Message(role=Role.USER, content="hi")])]

    assert len(chunks) == 1
    assert chunks[0].type == StreamChunkType.ERROR
    assert "agent exploded" in chunks[0].error


@pytest.mark.asyncio
async def test_pydantic_ai_generate_returns_chat_response(fake_agent: MagicMock) -> None:
    usage = MagicMock(request_tokens=1, response_tokens=1, total_tokens=2)
    run_result = MagicMock(data="final answer")
    run_result.usage.return_value = usage
    fake_agent.run = AsyncMock(return_value=run_result)

    provider = PydanticAIProvider(agent=fake_agent)
    result = await provider.generate([Message(role=Role.USER, content="hi")])

    assert result.content == "final answer"
    assert result.usage.total_tokens == 2
