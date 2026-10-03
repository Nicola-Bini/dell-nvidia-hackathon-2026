"""After a publish, replay what visitors ask so the cache is warm before the next one (S5).

The Serve API is local. A replay is best effort: if it is down the publish has already
succeeded, and only counts are ever logged or returned, never the replayed text.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import psycopg
import yaml
from cac_common.settings import Settings

log = logging.getLogger("cac.owner.prewarm")
INTENTS_FILE = Path(__file__).resolve().parents[4] / "demo" / "kenmore" / "intents.yaml"
TOP_LOGGED = 20
WORKERS = 2


def logged_texts(conn: psycopg.Connection, biz: str, limit: int = TOP_LOGGED) -> list[str]:
    rows = conn.execute(
        "SELECT text FROM ops.intent_log WHERE business_id = %s AND channel <> 'prewarm'"
        " AND kind IN ('answer', 'gap') GROUP BY text ORDER BY count(*) DESC, max(ts) DESC"
        " LIMIT %s", (biz, limit)).fetchall()
    return [r["text"] for r in rows]


def demo_texts(path: Path | None = None) -> list[str]:
    path = Path(os.environ.get("CAC_INTENTS_FILE") or path or INTENTS_FILE)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [str(i["text"]) for i in data.get("intents", []) if i.get("text")]


def texts_to_replay(conn: psycopg.Connection, biz: str) -> list[str]:
    seen, out = set(), []
    for text in [*logged_texts(conn, biz), *demo_texts()]:
        key = " ".join(text.lower().split())
        if key and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def serve_reachable(base: str, transport: httpx.BaseTransport | None) -> bool:
    try:
        with httpx.Client(transport=transport, timeout=1.0) as client:
            return client.get(f"{base}/healthz").status_code < 500
    except httpx.HTTPError:
        return False


def _one(client: httpx.Client, base: str, text: str) -> bool:
    try:
        resp = client.post(f"{base}/v1/intent", json={"text": text},
                           headers={"X-CAC-Channel": "prewarm"})
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def run(texts: list[str], base: str, transport: httpx.BaseTransport | None = None) -> dict:
    """Replay `texts` through POST /v1/intent with channel `prewarm`. Returns counts only."""
    with httpx.Client(transport=transport, timeout=20.0) as client, \
            ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda t: _one(client, base, t), texts))
    stats = {"sent": len(results), "ok": sum(results), "failed": len(results) - sum(results)}
    log.info("prewarm replayed %(sent)s intents, %(ok)s ok, %(failed)s failed", stats)
    return stats


def plan(conn: psycopg.Connection, settings: Settings,
         transport: httpx.BaseTransport | None) -> tuple[dict, list[str]]:
    """Decide what to replay. Returns the summary for the response and the texts to send."""
    base = settings.serve_base_url.rstrip("/")
    if not serve_reachable(base, transport):
        log.warning("prewarm skipped: serve api at %s is not reachable", base)
        return {"started": False, "skipped": "serve api unreachable"}, []
    texts = texts_to_replay(conn, settings.business_id)
    return {"started": True, "planned": len(texts)}, texts
