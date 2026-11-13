"""OpenAI provider adapter (requires the ``openai`` extra)."""

from __future__ import annotations

from typing import Any, AsyncIterator

from streaming_dash_chat.exceptions import ProviderError
from streaming_dash_chat.models import (
    ChatResponse,
    Message,
    StreamChunk,
    StreamChunkType,
    Usage,
)
from streaming_dash_chat.providers.base import BaseChatProvider

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - exercised via import error test
    AsyncOpenAI = None


class OpenAIProvider(BaseChatProvider):
    """Adapter around the official ``openai`` Python SDK's async client."""

    def __init__(
        self,
        model: str = "gpt-4.1",
        *,
        api_key: str | None = None,
        client: Any = None,
        system_prompt: str | None = None,
        **generation_kwargs: object,
    ) -> None:
        super().__init__(model=model, system_prompt=system_prompt, **generation_kwargs)
        if client is not None:
            self._client = client
        else:
            if AsyncOpenAI is None:
                raise ProviderError(
                    "The 'openai' package is required for OpenAIProvider. "
                    "Install it with: pip install \"streaming-dash-chat[openai]\""
                )
            # AsyncOpenAI() reads OPENAI_API_KEY from the environment when
            # api_key is None -- the key never needs to pass through
            # component config or reach the browser.
            self._client = AsyncOpenAI(api_key=api_key)

    def _to_openai_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        if self.system_prompt:
            out.append({"role": "system", "content": self.system_prompt})
        for message in messages:
            role = message.role.value if hasattr(message.role, "value") else message.role
            out.append({"role": role, "content": message.content})
        return out

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[StreamChunk]:
        params = {**self.generation_kwargs, **kwargs}
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=self._to_openai_messages(messages),
                stream=True,
                stream_options={"include_usage": True},
                **params,
            )
        except Exception as exc:  # noqa: BLE001 - normalize any SDK error
            yield StreamChunk(type=StreamChunkType.ERROR, error=str(exc))
            return

        usage: Usage | None = None
        try:
            async for event in response:
                choices = getattr(event, "choices", None)
                if choices:
                    delta = choices[0].delta
                    text = getattr(delta, "content", None)
                    if text:
                        yield StreamChunk(type=StreamChunkType.TOKEN, text=text)
                event_usage = getattr(event, "usage", None)
                if event_usage:
                    usage = Usage(
                        prompt_tokens=event_usage.prompt_tokens,
                        completion_tokens=event_usage.completion_tokens,
                        total_tokens=event_usage.total_tokens,
                    )
        except Exception as exc:  # noqa: BLE001
            yield StreamChunk(type=StreamChunkType.ERROR, error=str(exc))
            return

        yield StreamChunk(type=StreamChunkType.DONE, usage=usage)

    async def generate(self, messages: list[Message], **kwargs: object) -> ChatResponse:
        params = {**self.generation_kwargs, **kwargs}
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=self._to_openai_messages(messages),
                stream=False,
                **params,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

        choice = response.choices[0]
        raw_usage = getattr(response, "usage", None)
        usage = (
            Usage(
                prompt_tokens=raw_usage.prompt_tokens,
                completion_tokens=raw_usage.completion_tokens,
                total_tokens=raw_usage.total_tokens,
            )
            if raw_usage
            else None
        )
        return ChatResponse(content=choice.message.content or "", usage=usage)
