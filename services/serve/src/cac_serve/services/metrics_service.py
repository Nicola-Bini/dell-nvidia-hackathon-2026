"""GET /v1/metrics: exactly the keys in OWNERSHIP seam 3."""

from __future__ import annotations

from urllib.parse import urlsplit

import psycopg
from cac_common.settings import Settings
from psycopg_pool import PoolTimeout

from cac_serve.infra import db
from cac_serve.infra.metrics import metrics

_DEFAULT_PORTS = {"http": 80, "https": 443}


def model_host(llm_base_url: str) -> str:
    """`host:port` of the model endpoint the Serve API is configured to call."""
    parts = urlsplit(llm_base_url)
    port = parts.port or _DEFAULT_PORTS.get(parts.scheme, 80)
    host = parts.hostname or ""
    return f"[{host}]:{port}" if ":" in host else f"{host}:{port}"


def read_graph_version(business_id: str, timeout: float | None = None) -> int:
    """The published graph version, 0 when nothing is published."""
    with db.snapshot(timeout) as conn:
        row = conn.execute(
            "SELECT graph_version FROM kg_public.meta WHERE business_id = %s", (business_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def get_metrics(settings: Settings) -> dict:
    counters = metrics.snapshot()
    try:
        graph_version = read_graph_version(settings.business_id, timeout=1.0)
    except (psycopg.Error, PoolTimeout):
        graph_version = 0
    return {
        "latency_ms": counters["latency_ms"],
        "cache_hit_rate": counters["cache_hit_rate"],
        "model_calls": counters["model_calls"],
        "model_inflight": counters["model_inflight"],
        "graph_version": graph_version,
        "leads_captured": counters["leads_captured"],
        "cta_shown": counters["cta_shown"],
        "cta_clicked": counters["cta_clicked"],
        "model_host": model_host(settings.llm_base_url),
    }
