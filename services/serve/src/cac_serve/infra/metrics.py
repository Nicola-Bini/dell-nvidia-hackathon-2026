"""In-process counters for /v1/metrics. `cac_serve` cannot read the log, so they live here."""

from __future__ import annotations

import math
import threading
from collections import deque


def _percentile(ordered: list[float], fraction: float) -> int:
    if not ordered:
        return 0
    rank = max(1, math.ceil(fraction * len(ordered)))
    return round(ordered[rank - 1])


class Metrics:
    """Thread-safe counters and a sliding window of request latencies."""

    def __init__(self, window: int = 1000) -> None:
        self._lock = threading.Lock()
        self._window = window
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._latencies: deque[float] = deque(maxlen=self._window)
            self._latency_count = 0
            self._cache_hits = 0
            self._cache_lookups = 0
            self._model_calls = 0
            self._model_inflight = 0
            self._leads = 0
            self._cta_shown = 0
            self._cta_clicked = 0

    def record_latency(self, ms: float) -> None:
        with self._lock:
            self._latencies.append(ms)
            self._latency_count += 1

    def record_cache(self, hit: bool) -> None:
        with self._lock:
            self._cache_lookups += 1
            self._cache_hits += 1 if hit else 0

    def model_call_started(self) -> None:
        with self._lock:
            self._model_calls += 1
            self._model_inflight += 1

    def model_call_finished(self) -> None:
        with self._lock:
            self._model_inflight = max(0, self._model_inflight - 1)

    def incr_leads(self) -> None:
        with self._lock:
            self._leads += 1

    def incr_cta_shown(self) -> None:
        with self._lock:
            self._cta_shown += 1

    def incr_cta_clicked(self) -> None:
        with self._lock:
            self._cta_clicked += 1

    def snapshot(self) -> dict:
        """Counters only; the service adds `graph_version` and `model_host`."""
        with self._lock:
            ordered = sorted(self._latencies)
            lookups = self._cache_lookups
            latency = {"p50": _percentile(ordered, 0.50), "p95": _percentile(ordered, 0.95)}
            return {
                "latency_ms": latency,
                "latency_count": self._latency_count,
                "cache_hit_rate": round(self._cache_hits / lookups, 4) if lookups else 0.0,
                "model_calls": self._model_calls,
                "model_inflight": self._model_inflight,
                "leads_captured": self._leads,
                "cta_shown": self._cta_shown,
                "cta_clicked": self._cta_clicked,
            }


metrics = Metrics()
