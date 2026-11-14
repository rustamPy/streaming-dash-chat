"""Send / regenerate / cancel callbacks -- the core streaming machinery.

``handle_send`` and ``handle_regenerate`` are async-generator callbacks: Dash
streams each yield to the browser as it happens (NDJSON or WebSocket
transport), which is what gives genuine token-by-token rendering without any
custom JavaScript transport.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import dash
from dash import Input, Output, Patch, State, ctx, no_update
from dash import dcc as _dcc

from streaming_dash_chat.layout.message import render_error_message, render_message
from streaming_dash_chat.models import Message, Role, StreamChunkType
from streaming_dash_chat.services.conversation_manager import ConversationManager

if TYPE_CHECKING:
    from streaming_dash_chat.component import AIChat

logger = logging.getLogger(__name__)

_USER_FACING_ERROR = (
    "Something went wrong while generating a response. Please try again."
)

"""Static asset registration for the AIChat component."""


def register_message_callbacks(app: dash.Dash, registry: dict[str, "AIChat"]) -> None:
    @app.callback(
        Output({"type": "sdc-messages", "chat": dash.MATCH}, "children"),
        Output({"type": "sdc-active-content", "chat": dash.MATCH}, "children"),
        Output({"type": "sdc-active-bubble", "chat": dash.MATCH}, "style"),
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Output({"type": "sdc-cancel", "chat": dash.MATCH}, "disabled"),
        Output({"type": "sdc-input", "chat": dash.MATCH}, "value"),
        Input({"type": "sdc-send", "chat": dash.MATCH}, "n_clicks"),
        Input({"type": "sdc-input", "chat": dash.MATCH}, "n_submit"),
        State({"type": "sdc-input", "chat": dash.MATCH}, "value"),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    async def handle_send(_n_clicks, _n_submit, text, store_data):
        chat_id = ctx.triggered_id["chat"]
        chat = registry[chat_id]
        text = (text or "").strip()
        if not text:
            raise dash.exceptions.PreventUpdate
        async for update in _run_stream(chat, store_data, user_text=text):
            yield update

    @app.callback(
        Output(
            {"type": "sdc-messages", "chat": dash.MATCH},
            "children",
            allow_duplicate=True,
        ),
        Output(
            {"type": "sdc-active-content", "chat": dash.MATCH},
            "children",
            allow_duplicate=True,
        ),
        Output(
            {"type": "sdc-active-bubble", "chat": dash.MATCH},
            "style",
            allow_duplicate=True,
        ),
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Output(
            {"type": "sdc-cancel", "chat": dash.MATCH}, "disabled", allow_duplicate=True
        ),
        Output(
            {"type": "sdc-input", "chat": dash.MATCH}, "value", allow_duplicate=True
        ),
        Input(
            {"type": "sdc-regenerate", "chat": dash.MATCH, "message": dash.ALL},
            "n_clicks",
        ),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    async def handle_regenerate(n_clicks_list, store_data):
        if not any(n_clicks_list):
            raise dash.exceptions.PreventUpdate
        chat_id = ctx.triggered_id["chat"]
        clicked_message_id = ctx.triggered_id.get("message")
        chat = registry[chat_id]

        session_id = ConversationManager.resolve_session_id(store_data)
        conversation_id = (store_data or {}).get("conversation_id") or "default"
        history = chat.conversations.history(session_id, conversation_id)

        # Regenerate only ever targets the most recent assistant turn. The
        # button is shown on every assistant message, but clicking it on an
        # older one is a documented no-op rather than a truncate-and-replay
        # feature we don't have scope to build correctly right now.
        if (
            not history
            or history[-1].role != Role.ASSISTANT
            or history[-1].id != clicked_message_id
        ):
            raise dash.exceptions.PreventUpdate

        async for update in _run_stream(
            chat, store_data, user_text=None, remove_last_bubble=True
        ):
            yield update

    @app.callback(
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Input({"type": "sdc-cancel", "chat": dash.MATCH}, "n_clicks"),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    def handle_cancel(_n_clicks, store_data):
        chat_id = ctx.triggered_id["chat"]
        chat = registry[chat_id]
        stream_id = (store_data or {}).get("active_stream_id")
        if stream_id:
            chat.streams.cancel(stream_id)
        raise dash.exceptions.PreventUpdate


async def _run_stream(
    chat: "AIChat",
    store_data,
    *,
    user_text: str | None,
    remove_last_bubble: bool = False,
):
    """Shared body for ``handle_send``/``handle_regenerate``: yields the same
    6-tuple shape their Outputs expect at three points -- stream start,
    every token, and stream end -- so a new assistant turn never requires
    resending the whole message history."""
    store_data = dict(store_data or {})
    conversation_id = store_data.get("conversation_id") or "default"
    session_id = ConversationManager.resolve_session_id(store_data)
    stream_id = uuid.uuid4().hex

    start_patch = Patch()
    if remove_last_bubble:
        del start_patch[-1]
    if user_text is not None:
        start_patch.append(
            render_message(
                chat.config.id, Message(role=Role.USER, content=user_text), chat.config
            )
        )

    store_data["active_stream_id"] = stream_id
    store_data["is_streaming"] = True
    yield (
        start_patch,
        "",
        {"display": "flex"},
        dict(store_data),
        False,
        "" if user_text is not None else no_update,
    )

    accumulated = ""
    final_patch = Patch()
    if user_text is not None:
        agen = chat.engine.stream_reply(
            session_id, conversation_id, stream_id, user_text=user_text
        )
    else:
        agen = chat.engine.regenerate_reply(session_id, conversation_id, stream_id)

    async for chunk in agen:
        if chunk.type == StreamChunkType.TOKEN:
            accumulated += chunk.text
            yield (
                no_update,
                _dcc.Markdown(
                    accumulated,
                    className="sdc-message-markdown",
                    link_target="_blank",
                    highlight_config={
                        "theme": "dark" if chat.config.theme == "dark" else "light"
                    },
                ),
                no_update,
                no_update,
                no_update,
                no_update,
            )
        elif chunk.type == StreamChunkType.DONE:
            if accumulated:
                final_patch.append(
                    render_message(
                        chat.config.id,
                        Message(
                            id=chunk.message_id or uuid.uuid4().hex,
                            role=Role.ASSISTANT,
                            content=accumulated,
                        ),
                        chat.config,
                    )
                )
        elif chunk.type == StreamChunkType.ERROR:
            logger.error(
                "streaming_dash_chat provider error (chat=%s): %s",
                chat.config.id,
                chunk.error,
            )
            if accumulated:
                final_patch.append(
                    render_message(
                        chat.config.id,
                        Message(
                            id=chunk.message_id or uuid.uuid4().hex,
                            role=Role.ASSISTANT,
                            content=accumulated,
                        ),
                        chat.config,
                    )
                )
            final_patch.append(render_error_message(chat.config.id, _USER_FACING_ERROR))

    store_data["active_stream_id"] = None
    store_data["is_streaming"] = False
    yield (
        final_patch,
        "",
        {"display": "none"},
        dict(store_data),
        True,
        no_update,
    )
