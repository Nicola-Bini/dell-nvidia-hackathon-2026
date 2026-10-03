"""Shared fixtures for the Serve API tests. Needs `make db-up seed` (repo root) first."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from datetime import date
from pathlib import Path

import httpx
import psycopg
import pytest
import yaml
from cac_common.settings import Settings, get_settings
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SURFACES = REPO_ROOT / "fixtures" / "surfaces"
INTENTS = REPO_ROOT / "demo" / "kenmore" / "intents.yaml"
TODAY = date(2026, 10, 3)  # every date-dependent test is pinned to this day (SCHEMA 8.2)


def load_golden(name: str) -> dict:
    """A golden Surface from fixtures/surfaces, e.g. load_golden("menu_vegetarian")."""
    return json.loads((SURFACES / f"{name}.json").read_text(encoding="utf-8"))


def strip_volatile(surface: dict) -> dict:
    """Drop the fields that differ per request so a bound surface compares to a golden."""
    return {k: v for k, v in surface.items() if k not in ("surface_id", "meta")}


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture()
def serve_conn(settings: Settings):
    with psycopg.connect(settings.serve_database_url) as conn:
        yield conn


@pytest.fixture()
def owner_conn(settings: Settings):
    with psycopg.connect(settings.owner_database_url) as conn:
        yield conn


@pytest.fixture()
def graph(serve_conn, settings: Settings):
    from cac_serve.infra.graph_repo import load_graph

    return load_graph(serve_conn, settings.business_id)


# --- the 30-intent proof: uses tools/fake_llm unless CAC_INTENTS_REAL_MODEL=1 ---


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(url: str, seconds: float = 30.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise RuntimeError(f"model did not answer at {url}")


@pytest.fixture(scope="session")
def model_base_url():
    """The model the intents run against: the box model, or a private fake_llm."""
    if os.environ.get("CAC_INTENTS_REAL_MODEL") == "1":
        yield get_settings().llm_base_url
        return
    port = _free_port()
    process = subprocess.Popen(
        ["uv", "run", "--quiet", str(REPO_ROOT / "tools" / "fake_llm" / "server.py"),
         "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}/v1"
    try:
        _wait_for(f"{base_url}/models")
        yield base_url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def intents() -> list[dict]:
    return yaml.safe_load(INTENTS.read_text(encoding="utf-8"))["intents"]


@pytest.fixture(scope="session")
def intents_client(model_base_url):
    """The app wired to the model, pinned to 2026-10-03, starting from an empty cache."""
    os.environ["LLM_BASE_URL"] = model_base_url
    os.environ["CAC_TODAY"] = "2026-10-03"
    get_settings.cache_clear()
    settings = get_settings()
    with psycopg.connect(settings.owner_database_url) as conn:
        conn.execute("DELETE FROM ops.intent_cache")
    from cac_serve.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("CAC_TODAY", None)
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def golden():
    """Loader for a golden Surface by file stem, e.g. golden("off_topic")."""
    return load_golden


@pytest.fixture()
def client(model_base_url, monkeypatch):
    """A fresh app per test: dev database, the fake model, zeroed counters, pinned date."""
    from cac_serve.infra.metrics import metrics
    from cac_serve.infra.rate_limit import lead_limiter
    from cac_serve.main import create_app

    monkeypatch.setenv("LLM_BASE_URL", model_base_url)
    monkeypatch.setenv("CAC_TODAY", "2026-10-03")
    get_settings.cache_clear()
    metrics.reset()
    lead_limiter.reset()
    with TestClient(create_app(get_settings())) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def outcomes(intents_client, intents) -> dict[str, object]:
    """Each intent run once through the pipeline: text -> Outcome."""
    from cac_serve.services import pipeline

    settings = get_settings()
    today = pipeline.business_today(settings)
    return {row["text"]: pipeline.answer(row["text"], today, settings)[0] for row in intents}
