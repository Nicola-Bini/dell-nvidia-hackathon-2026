"""In-process sliding-window limits for lead submissions (SCHEMA 8.5).

Kept in memory because cac_serve cannot read ops.lead to count rows.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

WINDOW_S = 3600.0
PER_SESSION = 3
MCP_TOTAL = 10


class LeadLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _allow(self, key: str, limit: int) -> bool:
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= WINDOW_S:
            hits.popleft()
        return len(hits) < limit

    def try_acquire(self, session_id: str | None, channel: str) -> bool:
        """True and counted when the submission is within limits, else False."""
        keys = [(f"session:{session_id or 'anonymous'}", PER_SESSION)]
        if channel == "mcp":
            keys = [("channel:mcp", MCP_TOTAL)]
        with self._lock:
            if not all(self._allow(key, limit) for key, limit in keys):
                return False
            for key, _ in keys:
                self._hits[key].append(self._clock())
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


lead_limiter = LeadLimiter()
