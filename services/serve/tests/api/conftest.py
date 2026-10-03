"""Fixtures for the HTTP-level tests: an app wired to the dev database and fresh counters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cac_common.settings import Settings
from fastapi.testclient import TestClient

from cac_serve.infra.metrics import metrics
from cac_serve.main import create_app

SURFACES = Path(__file__).resolve().parents[4] / "fixtures" / "surfaces"


@pytest.fixture(scope="session")
def golden():
    """Loader for a golden Surface by file stem, e.g. golden("off_topic")."""

    def load(name: str) -> dict:
        return json.loads((SURFACES / f"{name}.json").read_text(encoding="utf-8"))

    return load


@pytest.fixture()
def client(settings: Settings):
    metrics.reset()
    with TestClient(create_app(settings)) as test_client:
        yield test_client
