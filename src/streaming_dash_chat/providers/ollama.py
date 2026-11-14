"""Ollama provider adapter for local models (requires the ``ollama`` extra)."""

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
    from ollama import AsyncClient
except ImportError:  # pragma: no cover
    AsyncClient = None


class OllamaProvider(BaseChatProvider):
    """Adapter around ``ollama.AsyncClient`` for locally hosted models.

    ``generation_kwargs`` are sent as Ollama ``options`` (e.g. temperature,
    num_ctx, top_p).
    """

    def __init__(
        self,
        model: str = "llama3.2",
        *,
        host: str = "http://localhost:11434",
        client: Any = None,
        system_prompt: str | None = None,
        **generation_kwargs: object,
    ) -> None:
        super().__init__(model=model, system_prompt=system_prompt, **generation_kwargs)
        if client is not None:
            self._client = client
        else:
            if AsyncClient is None:
                raise ProviderError(
                    "The 'ollama' package is required for OllamaProvider. "
                    'Install it with: pip install "streaming-dash-chat[ollama]"'
                )
            self._client = AsyncClient(host=host)

    def _to_ollama_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        if self.system_prompt:
            out.append({"role": "system", "content": self.system_prompt})
        for message in messages:
            role = (
                message.role.value if hasattr(message.role, "value") else message.role
            )
            out.append({"role": role, "content": message.content})
        return out

    @staticmethod
    def _usage(chunk: Any) -> Usage | None:
        prompt = getattr(chunk, "prompt_eval_count", None)
        completion = getattr(chunk, "eval_count", None)
        if prompt is None and completion is None:
            return None
        return Usage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=(prompt or 0) + (completion or 0),
        )

    async def stream(
        self, messages: list[Message], **kwargs: object
    ) -> AsyncIterator[StreamChunk]:
        options = {**self.generation_kwargs, **kwargs}
        usage: Usage | None = None
        try:
            response = await self._client.chat(
                model=self.model,
                messages=self._to_ollama_messages(messages),
                stream=True,
                options=options or None,
            )
            async for chunk in response:
                message = getattr(chunk, "message", None)
                text = getattr(message, "content", None) if message else None
                if text:
                    yield StreamChunk(type=StreamChunkType.TOKEN, text=text)
                if getattr(chunk, "done", False):
                    usage = self._usage(chunk)
        except Exception as exc:  # noqa: BLE001 - normalize any SDK/connection error
            yield StreamChunk(
                type=StreamChunkType.ERROR, error=_friendly(exc, self.model)
            )
            return

        yield StreamChunk(type=StreamChunkType.DONE, usage=usage)

    async def generate(self, messages: list[Message], **kwargs: object) -> ChatResponse:
        options = {**self.generation_kwargs, **kwargs}
        try:
            response = await self._client.chat(
                model=self.model,
                messages=self._to_ollama_messages(messages),
                stream=False,
                options=options or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(_friendly(exc, self.model)) from exc
        return ChatResponse(
            content=response.message.content or "",
            usage=self._usage(response),
        )


def _friendly(exc: Exception, model: str) -> str:
    text = str(exc)
    if "connect" in text.lower():
        return "Could not reach Ollama. Is it running? Start it with `ollama serve`."
    if "not found" in text.lower():
        return f"Model '{model}' not found. Pull it with `ollama pull {model}`."
    return text
