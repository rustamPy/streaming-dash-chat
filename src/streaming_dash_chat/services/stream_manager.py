"""Tracks in-flight streams so an explicit cancel request (not just a client
TCP disconnect) can stop a response.

Cancellation is a cooperative flag checked between chunks yielded by the
provider, not a hard cross-thread interrupt. Each Flask request runs its SSE
generator in its own thread with its own event loop (see
``callbacks/streaming.py``), so a ``threading.Event`` is the correct, simple
way to signal across the cancelling request's thread and the streaming
request's thread without touching asyncio internals from the wrong thread.
In practice this means cancellation takes effect at the next token boundary
(typically well under a second), not instantly mid-network-call -- a
documented trade-off, not an oversight.
"""

from __future__ import annotations

import threading


class StreamHandle:
    def __init__(self, stream_id: str) -> None:
        self.stream_id = stream_id
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()


class StreamManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streams: dict[str, StreamHandle] = {}

    def register(self, stream_id: str) -> StreamHandle:
        handle = StreamHandle(stream_id)
        with self._lock:
            self._streams[stream_id] = handle
        return handle

    def cancel(self, stream_id: str) -> bool:
        with self._lock:
            handle = self._streams.get(stream_id)
        if handle is None:
            return False
        handle.cancel()
        return True

    def unregister(self, stream_id: str) -> None:
        with self._lock:
            self._streams.pop(stream_id, None)
