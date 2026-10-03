"""GET /healthz: database, model and embedder, checked side by side so it answers within 1 s."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import httpx
import psycopg
from cac_common.settings import Settings
from psycopg_pool import PoolTimeout

from cac_serve.services.metrics_service import read_graph_version

_TIMEOUT_S = 0.5


def _check_database(business_id: str) -> tuple[str, int]:
    try:
        return "ok", read_graph_version(business_id, timeout=_TIMEOUT_S)
    except (psycopg.Error, PoolTimeout, RuntimeError):
        return "down", 0


def _check_endpoint(base_url: str) -> str:
    """`ok` when the OpenAI-compatible endpoint lists its models in time."""
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=_TIMEOUT_S)
    except httpx.HTTPError:
        return "down"
    return "ok" if response.status_code == 200 else "down"


def check_health(settings: Settings) -> dict:
    with ThreadPoolExecutor(max_workers=3) as pool:
        database = pool.submit(_check_database, settings.business_id)
        model = pool.submit(_check_endpoint, settings.llm_base_url)
        embedder = (
            pool.submit(_check_endpoint, settings.embed_base_url)
            if settings.embed_base_url else None
        )
        database_status, graph_version = database.result()
        model_status = model.result()
        embedder_status = embedder.result() if embedder else "disabled"
    healthy = database_status == "ok" and model_status == "ok" and embedder_status != "down"
    return {
        "status": "ok" if healthy else "degraded",
        "database": database_status,
        "model": model_status,
        "embedder": embedder_status,
        "graph_version": graph_version,
    }
