"""Tests for the Dash callback layer, exercising the exact generator logic
Dash's streaming callback dispatches to -- just invoked directly, since
driving it through Dash's HTTP/NDJSON transport needs a browser this
environment doesn't have. ``_run_stream`` is the real code path; only the
transport (Dash itself) is not re-tested here."""

from __future__ import annotations

import dash
import pytest

import streaming_dash_chat as sdc
from streaming_dash_chat.callbacks.messages import _run_stream
from streaming_dash_chat.providers.mock import MockProvider


def make_app_and_chat(**chat_kwargs) -> tuple[dash.Dash, "sdc.AIChat"]:
    app = dash.Dash(__name__, shared_storage=dash.LocalSharedStorage)
    chat = sdc.AIChat(id="test-chat", provider=MockProvider(reply="hi there", delay_seconds=0), **chat_kwargs)
    app.layout = chat.layout
    chat.register_callbacks(app)
    return app, chat


@pytest.mark.asyncio
async def test_run_stream_send_flow_yields_user_bubble_then_tokens_then_final():
    app, chat = make_app_and_chat()
    store_data = {"conversation_id": "c1", "active_stream_id": None, "is_streaming": False, "session_id": "sess-1"}

    updates = [u async for u in _run_stream(chat, store_data, user_text="hello")]

    # First frame: user bubble appended, active bubble revealed, store marks streaming.
    first = updates[0]
    messages_patch, active_content, active_style, new_store, cancel_disabled, input_value = first
    assert active_style == {"display": "flex"}
    assert new_store["is_streaming"] is True
    assert new_store["active_stream_id"]
    assert cancel_disabled is False
    assert input_value == ""

    # Middle frames: token updates only touch the active-bubble content Output.
    token_frames = updates[1:-1]
    assert len(token_frames) > 0
    for frame in token_frames:
        assert frame[0] is dash.no_update
        assert isinstance(frame[1], dash.development.base_component.Component)
        assert frame[2] is dash.no_update

    # Last frame: settles the assistant message, hides the active bubble, re-enables input.
    last = updates[-1]
    _, last_active_content, last_style, last_store, last_cancel_disabled, _ = last
    assert last_style == {"display": "none"}
    assert last_store["is_streaming"] is False
    assert last_store["active_stream_id"] is None
    assert last_cancel_disabled is True


@pytest.mark.asyncio
async def test_run_stream_persists_history_for_the_right_session():
    app, chat = make_app_and_chat()
    store_data = {"conversation_id": "c1", "active_stream_id": None, "is_streaming": False, "session_id": "sess-1"}

    async for _ in _run_stream(chat, store_data, user_text="hello"):
        pass

    history = chat.conversations.history("sess-1", "c1")
    assert [m.content for m in history] == ["hello", "hi there"]


@pytest.mark.asyncio
async def test_run_stream_cancel_mid_flight_stops_early():
    app, chat = make_app_and_chat()
    chat.engine.provider.delay_seconds = 0.05
    chat.engine.provider.reply = "one two three four five six seven"
    store_data = {"conversation_id": "c1", "active_stream_id": None, "is_streaming": False, "session_id": "sess-1"}

    received = []
    agen = _run_stream(chat, store_data, user_text="go")
    async for frame in agen:
        received.append(frame)
        if len(received) == 3:
            stream_id = received[0][3]["active_stream_id"]
            chat.streams.cancel(stream_id)

    last_messages_patch = received[-1][0]
    assert last_messages_patch is not None  # final patch still appended (error bubble included)
    assert received[-1][2] == {"display": "none"}
    assert len(received) < 9  # didn't stream all the way to natural completion
