"""Like/dislike/report callbacks. Feedback and reports are handed to
developer-supplied ``on_feedback``/``on_report`` callables -- this library
never hardcodes a storage backend."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import dash
from dash import Input, Output, State, ctx

from streaming_dash_chat.models import Feedback, FeedbackType, Report
from streaming_dash_chat.services.conversation_manager import ConversationManager

if TYPE_CHECKING:
    from streaming_dash_chat.component import AIChat

logger = logging.getLogger(__name__)


def register_feedback_callbacks(app: dash.Dash, registry: dict[str, "AIChat"]) -> None:
    @app.callback(
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Input(
            {"type": "sdc-like", "chat": dash.MATCH, "message": dash.ALL}, "n_clicks"
        ),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    def handle_like(n_clicks_list, store_data):
        if not any(n_clicks_list):
            raise dash.exceptions.PreventUpdate
        _record_feedback(
            registry,
            ctx.triggered_id["chat"],
            ctx.triggered_id.get("message"),
            FeedbackType.LIKE,
            store_data,
        )
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data", allow_duplicate=True),
        Input(
            {"type": "sdc-dislike", "chat": dash.MATCH, "message": dash.ALL}, "n_clicks"
        ),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    def handle_dislike(n_clicks_list, store_data):
        if not any(n_clicks_list):
            raise dash.exceptions.PreventUpdate
        _record_feedback(
            registry,
            ctx.triggered_id["chat"],
            ctx.triggered_id.get("message"),
            FeedbackType.DISLIKE,
            store_data,
        )
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output({"type": "sdc-report-modal", "chat": dash.MATCH}, "is_open"),
        Output({"type": "sdc-report-target", "chat": dash.MATCH}, "data"),
        Input(
            {"type": "sdc-report", "chat": dash.MATCH, "message": dash.ALL}, "n_clicks"
        ),
        Input({"type": "sdc-report-cancel", "chat": dash.MATCH}, "n_clicks"),
        Input({"type": "sdc-report-submit", "chat": dash.MATCH}, "n_clicks"),
        State({"type": "sdc-report-reason", "chat": dash.MATCH}, "value"),
        State({"type": "sdc-report-details", "chat": dash.MATCH}, "value"),
        State({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        State({"type": "sdc-report-target", "chat": dash.MATCH}, "data"),
        prevent_initial_call=True,
    )
    def handle_report(
        report_clicks,
        _cancel_clicks,
        _submit_clicks,
        reason,
        details,
        store_data,
        current_target,
    ):
        chat_id = ctx.triggered_id["chat"]
        triggered_type = ctx.triggered_id["type"]
        chat = registry[chat_id]

        if triggered_type == "sdc-report":
            if not any(report_clicks):
                raise dash.exceptions.PreventUpdate
            return True, ctx.triggered_id.get("message")

        if triggered_type == "sdc-report-cancel":
            return False, dash.no_update

        if triggered_type == "sdc-report-submit":
            if current_target and chat.on_report is not None:
                conversation_id = (store_data or {}).get("conversation_id") or "default"
                report = Report(
                    message_id=current_target,
                    conversation_id=conversation_id,
                    reason=reason or "Other",
                    details=details or None,
                )
                try:
                    chat.on_report(report)
                except (
                    Exception
                ):  # noqa: BLE001 - developer handler, never crash the app
                    logger.exception("on_report handler raised for chat=%s", chat_id)
            return False, dash.no_update

        raise dash.exceptions.PreventUpdate


def _record_feedback(
    registry: dict[str, "AIChat"],
    chat_id: str,
    message_id: str | None,
    feedback_type: FeedbackType,
    store_data,
) -> None:
    chat = registry[chat_id]

    session_id = ConversationManager.resolve_session_id(store_data)
    conversation_id = (store_data or {}).get("conversation_id") or "default"

    key = (session_id, message_id)
    if chat._feedback_state.get(key) == feedback_type:
        return  # duplicate submission of the same reaction -- ignore
    chat._feedback_state[key] = feedback_type

    feedback = Feedback(
        message_id=message_id,
        conversation_id=conversation_id,
        feedback_type=feedback_type,
        session_id=session_id,
    )
    chat.sinks.emit("on_feedback", feedback)
    if chat.on_feedback is not None:
        feedback = Feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            feedback_type=feedback_type,
        )
        try:
            chat.on_feedback(feedback)
        except Exception:  # noqa: BLE001 - developer handler, never crash the app
            logger.exception("on_feedback handler raised for chat=%s", chat_id)
