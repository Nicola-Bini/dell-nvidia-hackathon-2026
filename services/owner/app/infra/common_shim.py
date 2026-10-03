"""Stand-in for `cac_common` (OWNERSHIP seam 2) until blake's package is on origin/main.

Implements the three calls the seam fixes: `get_settings`, `reindex_node`, `publish`.
Delete this file and import `cac_common` once the package lands.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    business_id: str
    tz: str
    owner_database_url: str
    embed_base_url: str
    embed_model: str
    embed_dim: int
    serve_base_url: str
    owner_tools_token: str
    owner_inbox_token: str
    owner_channel_user_id: str
    autonomy: str
    gap_ask_min_sessions: int


def get_settings() -> Settings:
    _load_dotenv(REPO_ROOT / ".env")
    env = os.environ.get
    return Settings(
        business_id=env("CAC_BUSINESS_ID", "biz_demo"),
        tz=env("CAC_TZ", "America/New_York"),
        owner_database_url=env("OWNER_DATABASE_URL", ""),
        embed_base_url=env("EMBED_BASE_URL", ""),
        embed_model=env("EMBED_MODEL", "bge-m3"),
        embed_dim=int(env("EMBED_DIM", "1024")),
        serve_base_url=env("SERVE_BASE_URL", "http://127.0.0.1:8080"),
        owner_tools_token=env("OWNER_TOOLS_TOKEN", ""),
        owner_inbox_token=env("OWNER_INBOX_TOKEN", ""),
        owner_channel_user_id=env("OWNER_CHANNEL_USER_ID", "owner"),
        autonomy=env("CAC_AUTONOMY", "balanced"),
        gap_ask_min_sessions=int(env("GAP_ASK_MIN_SESSIONS", "1")),
    )


def _search_text(name: str, props: dict, public_props: list[str]) -> str:
    parts = [name]
    for key in public_props or []:
        value = props.get(key)
        if value is None or isinstance(value, dict):
            continue
        if isinstance(value, list):
            parts.extend(str(v) for v in value if not isinstance(v, dict))
        else:
            parts.append(str(value))
    return " ".join(p for p in parts if p).strip()


def _embed(text: str) -> list[float] | None:
    base = os.environ.get("EMBED_BASE_URL", "")
    if not base or not text:
        return None
    model = os.environ.get("EMBED_MODEL", "bge-m3")
    try:
        resp = httpx.post(f"{base.rstrip('/')}/embeddings",
                          json={"model": model, "input": text}, timeout=10)
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None  # full-text fallback


def reindex_node(conn, node_id: str) -> None:
    """Rebuild `search_text` from name and the label's public props; set `embedding`."""
    row = conn.execute(
        "SELECT n.name, n.props, l.public_props FROM kg.node n "
        "JOIN kg.label l ON l.label = n.label WHERE n.id = %s", (node_id,)).fetchone()
    if row is None:
        return
    name, props, public_props = _row_values(row)
    text = _search_text(name, props or {}, list(public_props or []))
    vec = _embed(text)
    literal = None if vec is None else "[" + ",".join(str(x) for x in vec) + "]"
    conn.execute(
        "UPDATE kg.node SET search_text = %s, embedding = %s::vector, updated_at = now() "
        "WHERE id = %s", (text, literal, node_id))


def _row_values(row):
    if isinstance(row, dict):
        return row["name"], row["props"], row["public_props"]
    return row


def publish(conn, business_id: str) -> int:
    """Call `kg.publish()` and return the new graph version."""
    row = conn.execute("SELECT kg.publish(%s) AS v", (business_id,)).fetchone()
    return row["v"] if isinstance(row, dict) else row[0]
