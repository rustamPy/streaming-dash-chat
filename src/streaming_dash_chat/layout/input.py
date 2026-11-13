"""The message composer: textarea + send/cancel buttons."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from streaming_dash_chat.config import AIChatConfig


def render_input(chat_id: str, config: AIChatConfig) -> html.Div:
    return html.Div(
        [
            dbc.Textarea(
                id={"type": "sdc-input", "chat": chat_id},
                placeholder="Message the assistant…",
                className="sdc-input",
                rows=1,
                submit_on_enter=True,
            ),
            html.Button(
                "Send",
                id={"type": "sdc-send", "chat": chat_id},
                className="sdc-send-btn",
                **{"aria-label": "Send message"},
            ),
            html.Button(
                "Stop",
                id={"type": "sdc-cancel", "chat": chat_id},
                className="sdc-cancel-btn",
                disabled=True,
                **{"aria-label": "Stop generating"},
            ),
        ],
        className="sdc-input-row",
    )
