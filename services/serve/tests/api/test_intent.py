"""POST /v1/intent through the whole pipeline (fake model): golden surfaces, 422 on bad text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SURFACES = Path(__file__).resolve().parents[4] / "fixtures" / "surfaces"
INDEX = json.loads((SURFACES / "index.json").read_text(encoding="utf-8"))


def _stable(surface: dict) -> dict:
    """A surface without the fields that differ per request."""
    return {k: v for k, v in surface.items() if k not in ("surface_id", "meta")}


def _post(client, text: str):
    return client.post("/v1/intent", json={"text": text, "session_id": "sess_test"})


@pytest.mark.parametrize(("text", "filename"), sorted(INDEX.items()))
def test_indexed_text_returns_its_golden(client, golden, text, filename):
    response = _post(client, text)
    assert response.status_code == 200
    assert _stable(response.json()) == _stable(golden(filename.removesuffix(".json")))
    assert response.json()["meta"]["cache"] in ("miss", "exact")


def test_surrounding_whitespace_is_trimmed_before_lookup(client, golden):
    body = _post(client, "  vegetarian options \n").json()
    assert _stable(body) == _stable(golden("menu_vegetarian"))


def test_unknown_text_returns_off_topic(client, golden):
    response = _post(client, "what is the airspeed of an unladen swallow")
    assert response.status_code == 200
    assert _stable(response.json()) == _stable(golden("off_topic"))


@pytest.mark.parametrize("text", ["", "   ", "x" * 301])
def test_bad_text_is_422(client, text):
    response = _post(client, text)
    assert response.status_code == 422
    assert "x" * 301 not in response.text


def test_300_characters_is_accepted(client):
    assert _post(client, "x" * 300).status_code == 200


def test_missing_session_id_is_422(client):
    assert client.post("/v1/intent", json={"text": "vegetarian options"}).status_code == 422


def test_intent_records_latency(client):
    from cac_serve.infra.metrics import metrics

    _post(client, "vegetarian options")
    assert metrics.snapshot()["latency_count"] == 1
