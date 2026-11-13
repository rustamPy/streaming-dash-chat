"""Core data models shared across providers, services, and callbacks."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """A single message in a conversation history."""

    id: str = Field(default_factory=_new_id)
    role: Role
    content: str
    created_at: float = Field(default_factory=time.time)
    name: str | None = None


class Usage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class StreamChunkType(str, Enum):
    TOKEN = "token"
    DONE = "done"
    ERROR = "error"


class StreamChunk(BaseModel):
    """A single increment produced by a provider's streaming generator."""

    type: StreamChunkType
    text: str = ""
    usage: Usage | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    """A complete, non-streamed provider response."""

    content: str
    usage: Usage | None = None
    raw: dict[str, Any] | None = None


class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class Feedback(BaseModel):
    message_id: str
    conversation_id: str
    feedback_type: FeedbackType
    timestamp: float = Field(default_factory=time.time)


class Report(BaseModel):
    message_id: str
    conversation_id: str
    reason: str
    details: str | None = None
    timestamp: float = Field(default_factory=time.time)
