"""Pluggable export sinks (e.g. ADLS) with non-blocking, failure-isolated dispatch."""

from __future__ import annotations

import asyncio
import atexit
import inspect
import logging
import threading
import time
from concurrent.futures import Future, wait
from typing import Sequence

from streaming_dash_chat.models import ConversationRecord, Message

logger = logging.getLogger(__name__)


class BaseChatSink:
    """Subclass and override what you need. Methods may be sync or async."""

    def on_conversation_updated(
        self, record: ConversationRecord
    ) -> None: ...  # after every completed turn
    def on_conversation_closed(
        self, record: ConversationRecord
    ) -> None: ...  # "New chat" pressed
    def on_feedback(self, feedback) -> None: ...
    def on_report(self, report) -> None: ...
    def on_event(self, event) -> None: ...


def build_record(
    chat_id, session_id, conversation_id, messages: list[Message], **extra
) -> ConversationRecord:
    return ConversationRecord(
        chat_id=chat_id,
        session_id=session_id,
        conversation_id=conversation_id,
        messages=messages,
        started_at=messages[0].created_at if messages else time.time(),
        **extra,
    )


class SinkDispatcher:
    """Runs all sink calls on one background event loop. emit() never blocks
    and never raises; a failing sink is logged and does not affect others."""

    def __init__(
        self, sinks: Sequence[BaseChatSink] = (), *, max_concurrency: int = 8
    ) -> None:
        self._sinks = list(sinks)
        self._max_concurrency = max_concurrency
        self._loop: asyncio.AbstractEventLoop | None = None
        self._sem: asyncio.Semaphore | None = None
        self._lock = threading.Lock()
        self._pending: set[Future] = set()
        self._started = threading.Event()

    def _ensure_started(self) -> None:
        with self._lock:
            if self._loop is not None:
                return

            def run() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                self._sem = asyncio.Semaphore(self._max_concurrency)
                self._started.set()
                loop.run_forever()

            threading.Thread(target=run, name="sdc-sinks", daemon=True).start()
            atexit.register(self.flush)
        self._started.wait()

    async def _deliver(self, method: str, payload) -> None:
        async with self._sem:
            for sink in self._sinks:
                fn = getattr(sink, method, None)
                if fn is None:
                    continue
                try:
                    if inspect.iscoroutinefunction(fn):
                        await fn(payload)
                    else:
                        await asyncio.to_thread(fn, payload)
                except Exception:  # noqa: BLE001
                    logger.exception("sink %r failed in %s", sink, method)

    def emit(self, method: str, payload) -> None:
        if not self._sinks:
            return
        try:
            self._ensure_started()
            fut = asyncio.run_coroutine_threadsafe(
                self._deliver(method, payload), self._loop
            )
            with self._lock:
                self._pending.add(fut)
            fut.add_done_callback(lambda f: self._pending.discard(f))
        except Exception:  # noqa: BLE001
            logger.exception("failed to dispatch %s", method)

    def flush(self, timeout: float = 15.0) -> None:
        with self._lock:
            pending = list(self._pending)
        if pending:
            wait(pending, timeout=timeout)
