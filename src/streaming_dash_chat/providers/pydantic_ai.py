"""PydanticAI provider adapter (requires the ``pydantic-ai`` extra).

PydanticAI's ``Agent`` is not an OpenAI-shaped client: it has its own
``run_stream`` async context manager, its own message types
(``ModelRequest``/``ModelResponse``), and its own usage accounting. This
adapter translates to and from those types explicitly rather than assuming
API parity with :class:`~streaming_dash_chat.providers.openai.OpenAIProvider`.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from streaming_dash_chat.exceptions import ProviderError
from streaming_dash_chat.models import (
    ChatResponse,
    Message,
    Role,
    StreamChunk,
    StreamChunkType,
    Usage,
)
from streaming_dash_chat.providers.base import BaseChatProvider

try:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
except ImportError:  # pragma: no cover - exercised via import error test
    Agent = None
    ModelRequest = ModelResponse = TextPart = UserPromptPart = None


class PydanticAIProvider(BaseChatProvider):
    """Adapter around a ``pydantic_ai.Agent``."""

    def __init__(
        self,
        model: str = "openai:gpt-4.1",
        *,
        agent: Any = None,
        system_prompt: str | None = None,
        deps: Any = None,
        tools: list[Any] | None = None,
        **generation_kwargs: object,
    ) -> None:
        super().__init__(model=model, system_prompt=system_prompt, **generation_kwargs)
        self.deps = deps
        if agent is not None:
            self._agent = agent
        else:
            if Agent is None:
                raise ProviderError(
                    "The 'pydantic-ai' package is required for PydanticAIProvider. "
                    "Install it with: pip install \"streaming-dash-chat[pydantic-ai]\""
                )
            self._agent = Agent(
                model,
                system_prompt=system_prompt or "",
                tools=tools or [],
                **generation_kwargs,
            )

    @staticmethod
    def _split_history(messages: list[Message]) -> tuple[list[Message], str]:
        if not messages or messages[-1].role != Role.USER:
            raise ProviderError("The last message in `messages` must be a user message.")
        return messages[:-1], messages[-1].content

    @staticmethod
    def _to_native_history(history: list[Message]) -> list[Any]:
        """Reconstruct PydanticAI's native message history from our generic
        :class:`Message` list, so prior turns round-trip through the agent
        the way PydanticAI expects, instead of being passed as plain
        OpenAI-style dicts."""
        native: list[Any] = []
        for message in history:
            if message.role == Role.SYSTEM:
                continue
            if message.role == Role.USER:
                native.append(ModelRequest(parts=[UserPromptPart(content=message.content)]))
            elif message.role == Role.ASSISTANT:
                native.append(ModelResponse(parts=[TextPart(content=message.content)]))
        return native

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[StreamChunk]:
        history, prompt = self._split_history(messages)
        try:
            async with self._agent.run_stream(
                prompt,
                message_history=self._to_native_history(history),
                deps=self.deps,
                **kwargs,
            ) as result:
                async for delta in result.stream_text(delta=True):
                    if delta:
                        yield StreamChunk(type=StreamChunkType.TOKEN, text=delta)

                usage = result.usage()
                yield StreamChunk(
                    type=StreamChunkType.DONE,
                    usage=Usage(
                        prompt_tokens=getattr(usage, "request_tokens", None),
                        completion_tokens=getattr(usage, "response_tokens", None),
                        total_tokens=getattr(usage, "total_tokens", None),
                    )
                    if usage
                    else None,
                )
        except Exception as exc:  # noqa: BLE001 - normalize any SDK error
            yield StreamChunk(type=StreamChunkType.ERROR, error=str(exc))

    async def generate(self, messages: list[Message], **kwargs: object) -> ChatResponse:
        history, prompt = self._split_history(messages)
        try:
            result = await self._agent.run(
                prompt,
                message_history=self._to_native_history(history),
                deps=self.deps,
                **kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

        usage = result.usage()
        return ChatResponse(
            content=str(result.data),
            usage=Usage(
                prompt_tokens=getattr(usage, "request_tokens", None),
                completion_tokens=getattr(usage, "response_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
            if usage
            else None,
        )
