"""Wires one Dash app's worth of pattern-matching callbacks, shared across
every AIChat instance registered on it."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import dash
from dash import ClientsideFunction, Input, Output
from flask import send_from_directory

from streaming_dash_chat.exceptions import ConfigurationError

if TYPE_CHECKING:
    from streaming_dash_chat.component import AIChat

_REGISTRY_ATTR = "_streaming_dash_chat_registry"
_REGISTERED_ATTR = "_streaming_dash_chat_callbacks_registered"
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_ASSETS_ROUTE = "/_streaming_dash_chat/assets/<path:filename>"
_ASSETS_URL_PREFIX = "/_streaming_dash_chat/assets"


def register_callbacks(app: dash.Dash, chat: "AIChat") -> None:
    """Register this chat instance and, the first time this is called for a
    given ``app``, the shared pattern-matching callbacks every AIChat
    instance relies on. Safe to call once per instance even when several
    instances share one app -- the callbacks themselves are only ever
    registered once (Dash raises on duplicate Outputs otherwise)."""
    _require_shared_storage(app)

    registry: dict[str, "AIChat"] | None = getattr(app, _REGISTRY_ATTR, None)
    if registry is None:
        registry = {}
        setattr(app, _REGISTRY_ATTR, registry)
    registry[chat.config.id] = chat

    if getattr(app, _REGISTERED_ATTR, False):
        return
    setattr(app, _REGISTERED_ATTR, True)

    # Imported lazily to avoid a circular import with streaming_dash_chat.component.
    from streaming_dash_chat.callbacks.conversation import (
        register_conversation_callbacks,
    )
    from streaming_dash_chat.callbacks.feedback import register_feedback_callbacks
    from streaming_dash_chat.callbacks.messages import register_message_callbacks

    register_message_callbacks(app, registry)
    register_feedback_callbacks(app, registry)
    register_conversation_callbacks(app, registry)
    register_assets(app)

    # Generates a per-browser-tab session_id into each chat's sessionStorage
    # -backed Store on first load (see assets/chat.js); self-referential but
    # safe, since the JS side returns no_update once session_id is already
    # set. This is what conversation isolation is keyed on -- see
    # ConversationManager.resolve_session_id for why it isn't a Flask cookie.
    app.clientside_callback(
        ClientsideFunction(
            namespace="streaming_dash_chat", function_name="ensureSessionId"
        ),
        Output({"type": "sdc-store", "chat": dash.MATCH}, "data"),
        Input({"type": "sdc-store", "chat": dash.MATCH}, "data"),
    )


def register_assets(app: dash.Dash) -> None:
    """Serve this package's bundled CSS/JS and wire them into the page.

    A plain ``assets/`` folder inside an installed library is *not*
    auto-served by Dash -- that convention only applies to the folder next
    to the developer's own app script. Dash's own supported mechanism for a
    non-component-boilerplate package to add CSS/JS is to serve the files
    itself and list the URLs in ``app.config.external_stylesheets`` /
    ``external_scripts``, which Dash re-reads on every index-page render
    (see ``Dash._generate_css_dist_html``/``_generate_scripts_html``) -- so
    appending here, before the app ever serves a request, is sufficient.
    """
    endpoint = "streaming_dash_chat_assets"
    if endpoint not in app.server.view_functions:
        app.server.add_url_rule(
            _ASSETS_ROUTE,
            endpoint=endpoint,
            view_func=lambda filename: send_from_directory(_ASSETS_DIR, filename),
        )

    css_url = f"{_ASSETS_URL_PREFIX}/chat.css"
    js_url = f"{_ASSETS_URL_PREFIX}/chat.js"
    if css_url not in app.config.external_stylesheets:
        app.config.external_stylesheets.append(css_url)
    if js_url not in app.config.external_scripts:
        app.config.external_scripts.append(js_url)


def _require_shared_storage(app: dash.Dash) -> None:
    """Dash's streaming callbacks (what AIChat's send/regenerate callbacks
    are) need a shared-storage backend to run over plain HTTP; without one,
    Dash itself raises ``StreamCallbackError`` the first time a message is
    sent, deep inside a request. Fail at registration time instead, with a
    message that points straight at the fix, since ``shared_storage`` can
    only be set when the ``Dash()`` app is constructed -- this library
    cannot patch it in after the fact."""
    if getattr(app, "shared_storage_enabled", False):
        return
    raise ConfigurationError(
        "streaming_dash_chat's streaming callbacks need Dash's shared-storage "
        "backend to run over plain HTTP. Construct your app with: "
        "Dash(__name__, shared_storage=dash.LocalSharedStorage) "
        "(in-memory, no extra dependency -- see Dash's shared_storage docs for "
        "Diskcache/Redis-backed alternatives in multi-worker deployments), or "
        "run the affected callbacks over WebSocket on an ASGI backend instead."
    )
