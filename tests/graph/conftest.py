"""Fixtures for the graph write-side tests (wp1).

They need the dev database seeded: `make db-up seed` (or `make db-reset seed`).
Run from the repo root: `uv run --project tests pytest tests/graph`.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
# scripts/ holds seedlib. packages/cac_common is added by path as well because macOS can flag
# the venv's editable-install .pth file as hidden, and Python 3.12 then skips it.
for _path in (ROOT / "scripts", ROOT / "packages" / "cac_common"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from cac_common.settings import Settings, get_settings  # noqa: E402  (needs the path above)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def business_id(settings: Settings) -> str:
    return settings.business_id


@pytest.fixture
def owner_conn(settings: Settings) -> Iterator[psycopg.Connection]:
    """Connection as cac_owner. Anything a test does not commit is rolled back."""
    with psycopg.connect(settings.owner_database_url) as conn:
        yield conn
        conn.rollback()


@pytest.fixture
def serve_conn(settings: Settings) -> Iterator[psycopg.Connection]:
    """Connection as cac_serve, the only role the Serve API uses."""
    with psycopg.connect(settings.serve_database_url, autocommit=True) as conn:
        yield conn
