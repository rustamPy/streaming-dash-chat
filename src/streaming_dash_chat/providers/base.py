"""Common provider interface implemented by each LLM backend adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from streaming_dash_chat.models import ChatResponse, Message, StreamChunk


class BaseChatProvider(ABC):
    """Base class every LLM backend adapter must implement.

    Subclasses normalize their SDK's request/response shapes into
    :class:`~streaming_dash_chat.models.StreamChunk` /
    :class:`~streaming_dash_chat.models.ChatResponse`, so the rest of the
    library never branches on provider type.
    """

    def __init__(
        self,
        model: str,
        *,
        system_prompt: str | None = None,
        **generation_kwargs: object,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.generation_kwargs = generation_kwargs

    @abstractmethod
    def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[StreamChunk]:
        """Stream a response as a sequence of :class:`StreamChunk`.

        Implementations are async generator functions. The final chunk must
        have ``type == StreamChunkType.DONE`` (success) or
        ``StreamChunkType.ERROR`` (failure); implementations must not raise
        out of the generator once streaming has started, so partial output
        already sent to the client isn't orphaned without an error chunk.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate(self, messages: list[Message], **kwargs: object) -> ChatResponse:
        """Generate a complete, non-streamed response."""
        raise NotImplementedError
