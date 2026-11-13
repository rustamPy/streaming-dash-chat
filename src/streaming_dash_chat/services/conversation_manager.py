"""Server-side conversation history storage.

The default in-memory store is per-process. Under a multi-worker WSGI/ASGI
deployment (gunicorn with >1 worker, multiple replicas, etc.) conversations
are *not* shared across workers -- a request handled by a different worker
than the one that holds the conversation will see an empty history. For
multi-worker deployments, supply a custom :class:`BaseConversationStore`
backed by Redis or a database instead of :class:`InMemoryConversationStore`.
This is documented in the README's Known Limitations section.
"""

from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from typing import Any

from streaming_dash_chat.models import Message

ConversationKey = tuple[str, str]  # (session_id, conversation_id)


class BaseConversationStore(ABC):
    """Pluggable backend for conversation history.

    A ``session_id`` scopes storage to one browser session so that a
    conversation_id supplied by the client can never be used to read or
    append to another session's conversation.
    """

    @abstractmethod
    def get_history(self, session_id: str, conversation_id: str) -> list[Message]: ...

    @abstractmethod
    def append(self, session_id: str, conversation_id: str, message: Message) -> None: ...

    @abstractmethod
    def clear(self, session_id: str, conversation_id: str) -> None: ...

    @abstractmethod
    def pop_last(self, session_id: str, conversation_id: str) -> Message | None: ...


class InMemoryConversationStore(BaseConversationStore):
    """Default, process-local conversation store. See module docstring for
    its multi-worker limitation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[ConversationKey, list[Message]] = {}

    def get_history(self, session_id: str, conversation_id: str) -> list[Message]:
        with self._lock:
            return list(self._data.get((session_id, conversation_id), []))

    def append(self, session_id: str, conversation_id: str, message: Message) -> None:
        with self._lock:
            self._data.setdefault((session_id, conversation_id), []).append(message)

    def clear(self, session_id: str, conversation_id: str) -> None:
        with self._lock:
            self._data.pop((session_id, conversation_id), None)

    def pop_last(self, session_id: str, conversation_id: str) -> Message | None:
        with self._lock:
            history = self._data.get((session_id, conversation_id))
            if history:
                return history.pop()
            return None


class ConversationManager:
    """Facade used by callbacks/the chat engine; delegates storage to a
    pluggable :class:`BaseConversationStore`."""

    def __init__(self, store: BaseConversationStore | None = None) -> None:
        self.store = store or InMemoryConversationStore()

    @staticmethod
    def resolve_session_id(store_data: dict[str, Any] | None) -> str:
        """Session scoping comes from a browser-``sessionStorage``-backed
        ``dcc.Store`` (see ``layout/chat.py`` and the clientside
        ``ensure_session_id`` callback), not a server-side cookie -- Dash's
        streaming callbacks don't run inside a Flask request context for
        their whole lifetime, so ``flask.session`` isn't usable here. The
        fallback below only fires in the sub-100ms window before that
        clientside callback has populated ``session_id`` on first page
        load; it's ephemeral (not persisted back), so an unlucky message
        sent in that window just won't share history with later ones --
        not a security issue, just a documented edge case.
        """
        session_id = (store_data or {}).get("session_id")
        return session_id or uuid.uuid4().hex

    def history(self, session_id: str, conversation_id: str) -> list[Message]:
        return self.store.get_history(session_id, conversation_id)

    def add_message(self, session_id: str, conversation_id: str, message: Message) -> None:
        self.store.append(session_id, conversation_id, message)

    def clear(self, session_id: str, conversation_id: str) -> None:
        self.store.clear(session_id, conversation_id)

    def pop_last(self, session_id: str, conversation_id: str) -> Message | None:
        return self.store.pop_last(session_id, conversation_id)
