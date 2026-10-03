"""Fixtures for the end-to-end tests. They talk to RUNNING services over HTTP:

    make db-up seed && make fake-llm && make serve          (the Serve API, this lane)
    the Owner tools API on OWNER_BASE_URL                    (je's lane)

A test module is skipped when the service it needs does not answer. Every test removes
what it added and republishes, so the seeded graph is left as it was found.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import httpx
import psycopg
import pytest
from cac_common.settings import Settings, get_settings


def _answers(base_url: str, path: str) -> bool:
    try:
        response = httpx.get(f"{base_url}{path}", timeout=2.0)
        return response.status_code == 200 and response.json().get("status") is not None
    except (httpx.HTTPError, ValueError, AttributeError):
        return False


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def serve(settings: Settings) -> Iterator[httpx.Client]:
    if not _answers(settings.serve_base_url, "/healthz"):
        pytest.skip(f"the Serve API is not running at {settings.serve_base_url}")
    with httpx.Client(base_url=settings.serve_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def owner_api(settings: Settings) -> Iterator[httpx.Client]:
    if not _answers(settings.owner_base_url, "/healthz"):
        pytest.skip(f"the Owner tools API is not running at {settings.owner_base_url}")
    with httpx.Client(base_url=settings.owner_base_url, timeout=60.0) as client:
        yield client


@pytest.fixture()
def owner_db(settings: Settings) -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.owner_database_url, autocommit=True) as conn:
        yield conn


@pytest.fixture()
def session_id(owner_db: psycopg.Connection) -> Iterator[str]:
    value = f"e2e-{uuid.uuid4()}"
    yield value
    owner_db.execute("DELETE FROM ops.lead WHERE session_id = %s", (value,))
