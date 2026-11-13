"""Renders a single settled (non-streaming) message bubble."""

from __future__ import annotations

import time

from dash import dcc, html

from streaming_dash_chat.config import AIChatConfig
from streaming_dash_chat.models import Message, Role

_HIGHLIGHT_CONFIG = {"theme": "dark"}


def render_message(chat_id: str, message: Message, config: AIChatConfig) -> html.Div:
    role = message.role.value if hasattr(message.role, "value") else message.role

    bubble_children = [
        dcc.Markdown(
            message.content,
            className="sdc-message-markdown",
            link_target="_blank",
            highlight_config={"theme": "dark" if config.theme == "dark" else "light"},
        )
    ]
    if config.show_timestamps:
        bubble_children.append(
            html.Div(
                time.strftime("%H:%M", time.localtime(message.created_at)),
                className="sdc-message-timestamp",
            )
        )
    if role == Role.ASSISTANT or role == "assistant":
        bubble_children.append(render_message_actions(chat_id, message, config))

    return html.Div(
        html.Div(bubble_children, className="sdc-message-bubble"),
        id={"type": "sdc-message", "chat": chat_id, "message": message.id},
        className=f"sdc-message sdc-message--{role}",
        **{"data-role": role},
    )


def render_message_actions(chat_id: str, message: Message, config: AIChatConfig) -> html.Div:
    buttons = [
        html.Button(
            "Copy",
            id={"type": "sdc-copy", "chat": chat_id, "message": message.id},
            className="sdc-action-btn sdc-copy-btn",
            title="Copy response",
            **{"data-copy-text": message.content},
        )
    ]
    if config.allow_feedback:
        buttons.append(
            html.Button(
                "Like",
                id={"type": "sdc-like", "chat": chat_id, "message": message.id},
                className="sdc-action-btn",
                title="Like this response",
            )
        )
        buttons.append(
            html.Button(
                "Dislike",
                id={"type": "sdc-dislike", "chat": chat_id, "message": message.id},
                className="sdc-action-btn",
                title="Dislike this response",
            )
        )
    if config.allow_report:
        buttons.append(
            html.Button(
                "Report",
                id={"type": "sdc-report", "chat": chat_id, "message": message.id},
                className="sdc-action-btn",
                title="Report this response",
            )
        )
    if config.allow_regenerate:
        buttons.append(
            html.Button(
                "Regenerate",
                id={"type": "sdc-regenerate", "chat": chat_id, "message": message.id},
                className="sdc-action-btn",
                title="Regenerate this response",
            )
        )
    return html.Div(
        buttons,
        className="sdc-message-actions",
        id={"type": "sdc-message-actions", "chat": chat_id, "message": message.id},
    )


def render_error_message(chat_id: str, text: str) -> html.Div:
    return html.Div(
        html.Div(text, className="sdc-message-bubble sdc-message-bubble--error"),
        className="sdc-message sdc-message--error",
        **{"data-role": "error"},
    )
