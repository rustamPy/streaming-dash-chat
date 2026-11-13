"""Typed exceptions for streaming_dash_chat."""

from __future__ import annotations


class StreamingDashChatError(Exception):
    """Base class for all library-raised exceptions."""


class ProviderError(StreamingDashChatError):
    """Raised when an LLM provider fails to generate or stream a response."""


class StreamCancelled(StreamingDashChatError):
    """Raised internally when a stream is cancelled by the client or server."""


class ConversationNotFoundError(StreamingDashChatError):
    """Raised when a conversation_id does not resolve to a known conversation
    for the requesting session."""


class ConfigurationError(StreamingDashChatError):
    """Raised when an AIChat component or provider is misconfigured."""
