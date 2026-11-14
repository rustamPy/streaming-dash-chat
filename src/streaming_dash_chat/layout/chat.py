"""Assembles the dbc.Offcanvas shell for one AIChat instance."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from streaming_dash_chat.config import AIChatConfig
from streaming_dash_chat.layout.feedback import render_report_modal
from streaming_dash_chat.layout.header import render_header
from streaming_dash_chat.layout.input import render_input
from streaming_dash_chat.layout.message import render_message
from streaming_dash_chat.models import Message, Role

_DEFAULT_WIDTH = "420px"
_DEFAULT_HEIGHT = "70vh"


def _offcanvas_style(config: AIChatConfig) -> dict[str, str]:
    if config.placement in ("top", "bottom"):
        return {"height": config.height or _DEFAULT_HEIGHT}
    return {"width": config.width or _DEFAULT_WIDTH}


def render_chat(config: AIChatConfig) -> html.Div:
    chat_id = config.id
    welcome_children = []
    if config.welcome_message:
        welcome_children.append(
            render_message(
                chat_id,
                Message(
                    id="welcome", role=Role.ASSISTANT, content=config.welcome_message
                ),
                config,
            )
        )

    offcanvas = dbc.Offcanvas(
        [
            render_header(chat_id, config),
            html.Div(
                [
                    html.Div(
                        welcome_children,
                        id={"type": "sdc-messages", "chat": chat_id},
                        className="sdc-messages",
                    ),
                    html.Div(
                        html.Div(id={"type": "sdc-active-content", "chat": chat_id}),
                        id={"type": "sdc-active-bubble", "chat": chat_id},
                        className="sdc-message sdc-message--assistant sdc-active-bubble",
                        style={"display": "none"},
                    ),
                ],
                className="sdc-scroll-area",
            ),
            render_input(chat_id, config),
            render_report_modal(chat_id),
            dcc.Store(
                id={"type": "sdc-store", "chat": chat_id},
                storage_type="session",
                data={
                    "conversation_id": "default",
                    "active_stream_id": None,
                    "is_streaming": False,
                    "session_id": None,
                },
            ),
        ],
        id={"type": "sdc-offcanvas", "chat": chat_id},
        title=None,
        is_open=config.is_open,
        placement=config.placement,
        close_button=False,
        style=_offcanvas_style(config),
        className=f"sdc-root sdc-offcanvas sdc-theme--{config.theme}"
        + (f" {config.class_name}" if config.class_name else ""),
    )

    toggle_button = (
        html.Button(
            "Chat",
            id={"type": "sdc-toggle", "chat": chat_id},
            className="sdc-toggle-btn",
            **{"aria-label": "Open chat"},
        )
        if config.show_toggle_button
        else None
    )

    return html.Div(
        [toggle_button, offcanvas], className="sdc-root", id=f"{chat_id}-root"
    )
