"""Typed view of the environment variables in .env.example (docs/SCHEMA.md section 2).

Precedence: process environment, then the nearest `.env` above the working directory, then
the laptop defaults below.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DEFAULTS = {
    "CAC_BUSINESS_ID": "biz_demo",
    "CAC_TZ": "America/New_York",
    "SERVE_DATABASE_URL": "postgresql://cac_serve:cac_serve_dev@127.0.0.1:54320/cac",
    "OWNER_DATABASE_URL": "postgresql://cac_owner:cac_owner_dev@127.0.0.1:54320/cac",
    "LLM_BASE_URL": "http://127.0.0.1:8000/v1",
    "LLM_MODEL": "qwen3.6:35b",
    "MODEL_MAX_INFLIGHT": "4",
    "EMBED_BASE_URL": "",
    "EMBED_MODEL": "bge-m3",
    "EMBED_DIM": "1024",
    "SERVE_PORT": "8080",
    "SERVE_BASE_URL": "http://127.0.0.1:8080",
    "OWNER_BASE_URL": "http://127.0.0.1:8081",
    "OWNER_TOOLS_TOKEN": "dev-agent-token",
    "OWNER_INBOX_TOKEN": "dev-inbox-token",
    "OWNER_CHANNEL_USER_ID": "owner",
    "CAC_AUTONOMY": "balanced",
    "GAP_ASK_MIN_SESSIONS": "1",
    "INTENT_MAX_CHARS": "300",
    "CAC_ALLOWED_ORIGINS": "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173",
}


@dataclass(frozen=True)
class Settings:
    business_id: str
    tz: str
    serve_database_url: str
    owner_database_url: str
    llm_base_url: str
    llm_model: str
    model_max_inflight: int
    embed_base_url: str
    embed_model: str
    embed_dim: int
    serve_port: int
    serve_base_url: str
    owner_base_url: str
    owner_tools_token: str
    owner_inbox_token: str
    owner_channel_user_id: str
    autonomy: str
    gap_ask_min_sessions: int
    intent_max_chars: int
    allowed_origins: tuple[str, ...]


def _parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _nearest_env_file(start: Path) -> dict[str, str]:
    for folder in (start, *start.parents):
        candidate = folder / ".env"
        if candidate.is_file():
            return _parse_env_file(candidate.read_text(encoding="utf-8"))
    return {}


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Build Settings from `environ` (default: the process environment plus `.env`)."""
    if environ is None:
        environ = {**_nearest_env_file(Path.cwd()), **os.environ}
    get = lambda key: environ.get(key, _DEFAULTS[key])  # noqa: E731
    origins = tuple(o.strip() for o in get("CAC_ALLOWED_ORIGINS").split(",") if o.strip())
    return Settings(
        business_id=get("CAC_BUSINESS_ID"),
        tz=get("CAC_TZ"),
        serve_database_url=get("SERVE_DATABASE_URL"),
        owner_database_url=get("OWNER_DATABASE_URL"),
        llm_base_url=get("LLM_BASE_URL"),
        llm_model=get("LLM_MODEL"),
        model_max_inflight=int(get("MODEL_MAX_INFLIGHT")),
        embed_base_url=get("EMBED_BASE_URL"),
        embed_model=get("EMBED_MODEL"),
        embed_dim=int(get("EMBED_DIM")),
        serve_port=int(get("SERVE_PORT")),
        serve_base_url=get("SERVE_BASE_URL"),
        owner_base_url=get("OWNER_BASE_URL"),
        owner_tools_token=get("OWNER_TOOLS_TOKEN"),
        owner_inbox_token=get("OWNER_INBOX_TOKEN"),
        owner_channel_user_id=get("OWNER_CHANNEL_USER_ID"),
        autonomy=get("CAC_AUTONOMY"),
        gap_ask_min_sessions=int(get("GAP_ASK_MIN_SESSIONS")),
        intent_max_chars=int(get("INTENT_MAX_CHARS")),
        allowed_origins=origins,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
