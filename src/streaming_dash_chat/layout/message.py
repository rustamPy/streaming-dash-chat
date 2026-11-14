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

    children = [html.Div(bubble_children, className="sdc-message-bubble")]
    if role == Role.ASSISTANT or role == "assistant":
        children.append(
            render_message_actions(chat_id, message, config)
        )  # outside the bubble

    return html.Div(
        children,
        id={"type": "sdc-message", "chat": chat_id, "message": message.id},
        className=f"sdc-message sdc-message--{role}",
        **{"data-role": role},
    )


def _action_button(
    chat_id, message, kind: str, label: str, *, toggle: bool = False, extra=None
):
    props = {
        "id": {"type": f"sdc-{kind}", "chat": chat_id, "message": message.id},
        "className": f"sdc-action-btn sdc-icon--{kind}"
        + (" sdc-copy-btn" if kind == "copy" else ""),
        "title": label,
        "aria-label": label,
        "type": "button",
    }
    if toggle:
        props["aria-pressed"] = "false"
    if extra:
        props.update(extra)
    return html.Button(**props)


def render_message_actions(
    chat_id: str, message: Message, config: AIChatConfig
) -> html.Div:
    buttons = [
        _action_button(
            chat_id, message, "copy", "Copy", extra={"data-copy-text": message.content}
        ),
    ]
    if config.allow_feedback:
        buttons.append(
            _action_button(chat_id, message, "like", "Good response", toggle=True)
        )
        buttons.append(
            _action_button(chat_id, message, "dislike", "Bad response", toggle=True)
        )
    if config.allow_regenerate:
        buttons.append(_action_button(chat_id, message, "regenerate", "Retry"))
    if config.allow_report:
        buttons.append(_action_button(chat_id, message, "report", "Report"))

    return html.Div(
        buttons,
        className="sdc-message-actions",
        role="toolbar",
        id={"type": "sdc-message-actions", "chat": chat_id, "message": message.id},
        **{"aria-label": "Message actions"},
    )


def render_error_message(chat_id: str, text: str) -> html.Div:
    return html.Div(
        html.Div(text, className="sdc-message-bubble sdc-message-bubble--error"),
        className="sdc-message sdc-message--error",
        **{"data-role": "error"},
    )
