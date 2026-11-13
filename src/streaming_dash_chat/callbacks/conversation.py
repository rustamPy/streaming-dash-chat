"""Offcanvas open/close and new-conversation callbacks."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import dash
from dash import Input, Output, State, ctx

from streaming_dash_chat.layout.message import render_message
from streaming_dash_chat.models import Message, Role
from streaming_dash_chat.services.conversation_manager import ConversationManager

if TYPE_CHECKING:
    from streaming_dash_chat.component import AIChat


def register_conversation_callbacks(app: dash.Dash, registry: dict[str, "AIChat"]) -> None:
    @app.callback(
        Output({"type": "sdc-offcanvas", "chat": dash.MATCH}, "is_open"),
        Input({"type": "sdc-toggle", "chat": dash.MATCH}, "n_clicks"),
        Input({"type": "sdc-close", "chat": dash.MATCH}, "n_clicks"),
        State({"type": "sdc-offcanvas", "chat": dash.MATCH}, "is_open"),
        prevent_initial_call=True,
    )
    def toggle_offcanvas(_toggle_clicks, _close_clicks, is_open):
        if ctx.triggered_id["type"] == "sdc-close":
            return False
        return not is_open

    @app.callback(
        Output({"type": "sdc-messages", "chat": dash.MATCH}, "children", allow_duplicate=True),
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Output({"type": "sdc-active-bubble", "chat": dash.MATCH}, "style", allow_duplicate=True),
        Input({"type": "sdc-new-conversation", "chat": dash.MATCH}, "n_clicks"),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    def new_conversation(_n_clicks, store_data):
        chat_id = ctx.triggered_id["chat"]
        chat = registry[chat_id]

        session_id = ConversationManager.resolve_session_id(store_data)
        old_conversation_id = (store_data or {}).get("conversation_id") or "default"
        chat.conversations.clear(session_id, old_conversation_id)

        store_data = dict(store_data or {})
        store_data["conversation_id"] = uuid.uuid4().hex
        store_data["active_stream_id"] = None
        store_data["is_streaming"] = False

        welcome = []
        if chat.config.welcome_message:
            welcome = [
                render_message(
                    chat_id,
                    Message(id="welcome", role=Role.ASSISTANT, content=chat.config.welcome_message),
                    chat.config,
                )
            ]
        return welcome, store_data, {"display": "none"}
