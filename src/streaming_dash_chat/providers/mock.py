"""A deterministic, dependency-free provider for tests, local development,
and demos that run without an LLM API key. Not a real LLM backend."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from streaming_dash_chat.models import ChatResponse, Message, StreamChunk, StreamChunkType, Usage
from streaming_dash_chat.providers.base import BaseChatProvider


class MockProvider(BaseChatProvider):
    """Streams a fixed reply token-by-token with a configurable delay.

    ``reply`` is split on whitespace boundaries (keeping the separators) so
    consumers see realistic incremental chunks rather than one giant blob.
    """

    def __init__(
        self,
        reply: str = "This is a mocked streaming response used for local development and tests.",
        *,
        delay_seconds: float = 0.02,
        fail_with: str | None = None,
        model: str = "mock",
        **generation_kwargs: object,
    ) -> None:
        super().__init__(model=model, **generation_kwargs)
        self.reply = reply
        self.delay_seconds = delay_seconds
        self.fail_with = fail_with

    def _tokens(self) -> list[str]:
        tokens: list[str] = []
        current = ""
        for char in self.reply:
            current += char
            if char == " ":
                tokens.append(current)
                current = ""
        if current:
            tokens.append(current)
        return tokens

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[StreamChunk]:
        if self.fail_with is not None:
            await asyncio.sleep(self.delay_seconds)
            yield StreamChunk(type=StreamChunkType.ERROR, error=self.fail_with)
            return

        for token in self._tokens():
            await asyncio.sleep(self.delay_seconds)
            yield StreamChunk(type=StreamChunkType.TOKEN, text=token)

        yield StreamChunk(
            type=StreamChunkType.DONE,
            usage=Usage(
                prompt_tokens=sum(len(m.content) for m in messages),
                completion_tokens=len(self.reply),
                total_tokens=sum(len(m.content) for m in messages) + len(self.reply),
            ),
        )

    async def generate(self, messages: list[Message], **kwargs: object) -> ChatResponse:
        return ChatResponse(content=self.reply)
