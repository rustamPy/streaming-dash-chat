"""streaming_dash_chat: a reusable, streaming AI chat component for Plotly Dash."""

from streaming_dash_chat.component import AIChat
from streaming_dash_chat.config import AIChatConfig, Placement, Theme
from streaming_dash_chat.models import (
    ChatResponse,
    Feedback,
    FeedbackType,
    Message,
    Report,
    Role,
    StreamChunk,
    StreamChunkType,
    Usage,
)

__version__ = "0.1.0"

__all__ = [
    "AIChat",
    "AIChatConfig",
    "Placement",
    "Theme",
    "Message",
    "Role",
    "StreamChunk",
    "StreamChunkType",
    "ChatResponse",
    "Usage",
    "Feedback",
    "FeedbackType",
    "Report",
    "__version__",
]
