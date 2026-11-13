"""Tests for AIChat construction/config, all 4 Offcanvas placements,
multi-instance isolation, and feedback/report submission."""

from __future__ import annotations

import dash
import pytest
from pydantic import ValidationError

import streaming_dash_chat as sdc
from streaming_dash_chat.models import FeedbackType
from streaming_dash_chat.providers.mock import MockProvider


def test_aichat_constructs_with_defaults():
    chat = sdc.AIChat(id="chat1", provider=MockProvider())
    assert chat.config.id == "chat1"
    assert chat.config.placement == "end"
    assert chat.config.is_open is False


@pytest.mark.parametrize("placement", ["start", "end", "top", "bottom"])
def test_all_four_placements_render(placement):
    chat = sdc.AIChat(id="chat1", provider=MockProvider(), placement=placement)
    layout = chat.layout
    offcanvas = layout.children[1]
    assert offcanvas.placement == placement
    if placement in ("top", "bottom"):
        assert "height" in offcanvas.style
    else:
        assert "width" in offcanvas.style


def test_invalid_placement_is_rejected():
    with pytest.raises(ValidationError):
        sdc.AIChat(id="chat1", provider=MockProvider(), placement="sideways")


def test_invalid_theme_is_rejected():
    with pytest.raises(ValidationError):
        sdc.AIChat(id="chat1", provider=MockProvider(), theme="neon")


def test_custom_title_subtitle_and_welcome_message_are_applied():
    chat = sdc.AIChat(
        id="chat1",
        provider=MockProvider(),
        title="Support Bot",
        subtitle="We usually reply instantly",
        welcome_message="Welcome aboard!",
    )
    assert chat.config.title == "Support Bot"
    assert chat.config.subtitle == "We usually reply instantly"
    assert chat.config.welcome_message == "Welcome aboard!"


def test_multiple_chat_instances_share_one_app_without_id_collisions():
    app = dash.Dash(__name__, shared_storage=dash.LocalSharedStorage)
    chat_a = sdc.AIChat(id="chat-a", provider=MockProvider())
    chat_b = sdc.AIChat(id="chat-b", provider=MockProvider())

    from dash import html

    app.layout = html.Div([chat_a.layout, chat_b.layout])
    chat_a.register_callbacks(app)
    chat_b.register_callbacks(app)  # must not raise (duplicate Output) the 2nd time

    registry = app._streaming_dash_chat_registry
    assert set(registry) == {"chat-a", "chat-b"}
    assert registry["chat-a"] is chat_a
    assert registry["chat-b"] is chat_b
    # Each instance keeps its own engine/provider/conversation state.
    assert chat_a.conversations is not chat_b.conversations
    assert chat_a.streams is not chat_b.streams


def test_feedback_handler_receives_feedback_and_dedupes_repeats():
    received = []
    chat = sdc.AIChat(id="chat1", provider=MockProvider(), on_feedback=received.append)

    from streaming_dash_chat.callbacks.feedback import _record_feedback

    app = dash.Dash(__name__, shared_storage=dash.LocalSharedStorage)
    chat.register_callbacks(app)
    registry = {"chat1": chat}

    store_data = {"conversation_id": "c1", "session_id": "sess-1"}
    _record_feedback(registry, "chat1", "m1", FeedbackType.LIKE, store_data)
    _record_feedback(registry, "chat1", "m1", FeedbackType.LIKE, store_data)  # duplicate, ignored
    _record_feedback(registry, "chat1", "m1", FeedbackType.DISLIKE, store_data)  # change, allowed

    assert len(received) == 2
    assert received[0].feedback_type == FeedbackType.LIKE
    assert received[1].feedback_type == FeedbackType.DISLIKE
    assert received[0].message_id == "m1"
    assert received[0].conversation_id == "c1"


def test_report_handler_receives_report():
    received = []
    chat = sdc.AIChat(id="chat1", provider=MockProvider(), on_report=received.append)

    from streaming_dash_chat.models import Report

    report = Report(message_id="m1", conversation_id="c1", reason="Other", details="details here")
    chat.on_report(report)

    assert len(received) == 1
    assert received[0].reason == "Other"
    assert received[0].details == "details here"
