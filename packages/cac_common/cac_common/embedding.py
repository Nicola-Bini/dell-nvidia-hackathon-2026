"""Embeddings from the local embedder (`EMBED_BASE_URL`), or None when there is none.

The endpoint is OpenAI-compatible and must be local; there is no cloud client here.
"""

from __future__ import annotations

import httpx

from cac_common.settings import get_settings

TIMEOUT_SECONDS = 10.0


def embed(texts: list[str]) -> list[list[float]] | None:
    """Return one vector per text, in input order.

    Returns None when `EMBED_BASE_URL` is empty (callers fall back to full-text search).
    Raises `httpx.HTTPError` when the embedder is configured but fails.
    """
    settings = get_settings()
    base_url = settings.embed_base_url.strip().rstrip("/")
    if not base_url:
        return None
    if not texts:
        return []
    response = httpx.post(
        f"{base_url}/embeddings",
        json={"model": settings.embed_model, "input": texts},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    rows = sorted(response.json()["data"], key=lambda row: row.get("index", 0))
    return [row["embedding"] for row in rows]
