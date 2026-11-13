"""The public AIChat component."""

from __future__ import annotations

from typing import Callable

import dash

from streaming_dash_chat.callbacks.registration import (
    register_callbacks as _register_callbacks,
)
from streaming_dash_chat.config import AIChatConfig
from streaming_dash_chat.layout.chat import render_chat
from streaming_dash_chat.models import Feedback, FeedbackType, Report
from streaming_dash_chat.providers.base import BaseChatProvider
from streaming_dash_chat.services.chat_engine import ChatEngine
from streaming_dash_chat.services.conversation_manager import ConversationManager
from streaming_dash_chat.services.stream_manager import StreamManager

FeedbackHandler = Callable[[Feedback], None]
ReportHandler = Callable[[Report], None]


class AIChat:
    """A reusable, streaming AI chat component for Plotly Dash.

    Usage::

        from streaming_dash_chat import AIChat
        from streaming_dash_chat.providers import OpenAIProvider

        chat = AIChat(id="assistant-chat", provider=OpenAIProvider(model="gpt-4.1"))
        app.layout = html.Div([chat.layout, ...])
        chat.register_callbacks(app)

    Multiple ``AIChat`` instances may share one ``app``; call
    ``register_callbacks`` on each of them (duplicate callback registration
    is handled automatically).
    """

    def __init__(
        self,
        id: str,
        provider: BaseChatProvider,
        *,
        placement: str = "end",
        is_open: bool = False,
        width: str | None = None,
        height: str | None = None,
        title: str = "Assistant",
        subtitle: str | None = None,
        theme: str = "light",
        class_name: str | None = None,
        welcome_message: str | None = "Hi! How can I help you today?",
        assistant_name: str = "Assistant",
        avatar: str | None = None,
        allow_regenerate: bool = True,
        allow_feedback: bool = True,
        allow_report: bool = True,
        show_timestamps: bool = False,
        show_toggle_button: bool = True,
        on_feedback: FeedbackHandler | None = None,
        on_report: ReportHandler | None = None,
        conversation_manager: ConversationManager | None = None,
    ) -> None:
        self.config = AIChatConfig(
            id=id,
            placement=placement,
            is_open=is_open,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            theme=theme,
            class_name=class_name,
            welcome_message=welcome_message,
            assistant_name=assistant_name,
            avatar=avatar,
            allow_regenerate=allow_regenerate,
            allow_feedback=allow_feedback,
            allow_report=allow_report,
            show_timestamps=show_timestamps,
            show_toggle_button=show_toggle_button,
        )
        self.provider = provider
        self.on_feedback = on_feedback
        self.on_report = on_report
        self.conversations = conversation_manager or ConversationManager()
        self.streams = StreamManager()
        self.engine = ChatEngine(self.provider, self.conversations, self.streams)
        self._feedback_state: dict[tuple[str, str | None], FeedbackType] = {}

    def render(self) -> dash.development.base_component.Component:
        return render_chat(self.config)

    @property
    def layout(self) -> dash.development.base_component.Component:
        return self.render()

    def register_callbacks(self, app: dash.Dash) -> None:
        _register_callbacks(app, self)
