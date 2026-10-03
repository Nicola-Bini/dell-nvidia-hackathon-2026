"""Bootstrap, presets, actions, metrics, health and CORS."""

from __future__ import annotations

import pytest

METRIC_KEYS = {"latency_ms", "cache_hit_rate", "model_calls", "model_inflight", "graph_version",
               "leads_captured", "cta_shown", "cta_clicked", "model_host"}


def test_metrics_has_exactly_the_contract_keys(client):
    body = client.get("/v1/metrics").json()
    assert set(body) == METRIC_KEYS
    assert set(body["latency_ms"]) == {"p50", "p95"}
    assert body["model_host"] == "127.0.0.1:8000"
    assert isinstance(body["cache_hit_rate"], float)
    assert isinstance(body["graph_version"], int)


def test_metrics_latency_percentiles_follow_requests(client):
    for _ in range(3):
        client.post("/v1/intent", json={"text": "tell me a joke", "session_id": "s1"})
    latency = client.get("/v1/metrics").json()["latency_ms"]
    assert latency["p95"] >= latency["p50"] >= 0


def test_view_menu_is_the_preset_golden(client, golden):
    response = client.get("/v1/view/menu")
    assert response.status_code == 200
    assert response.json() == golden("preset_menu")


@pytest.mark.parametrize(
    ("preset", "component"),
    [("booking", "BookingForm"), ("catering", "CateringQuoteForm"), ("hours", "HoursCard")],
)
def test_other_presets_are_preset_surfaces(client, preset, component):
    body = client.get(f"/v1/view/{preset}").json()
    assert body["kind"] == "preset"
    assert body["meta"]["cache"] == "preset"
    assert body["views"][0]["component"] == component
    if preset != "hours":
        assert body["views"][0]["data"]["prefill"] == {}
        assert "40" not in body["views"][0]["text"]
        assert "2026-10-09" not in body["views"][0]["text"]


def test_unknown_preset_is_404(client):
    assert client.get("/v1/view/nope").status_code == 404


def test_src_cta_bumps_cta_clicked(client):
    client.get("/v1/view/booking")
    assert client.get("/v1/metrics").json()["cta_clicked"] == 0
    client.get("/v1/view/booking?src=cta")
    client.get("/v1/view/nope?src=cta")
    assert client.get("/v1/metrics").json()["cta_clicked"] == 1


@pytest.mark.parametrize("name", ["submit_booking_request", "submit_catering_quote", "submit_form"])
def test_known_actions_are_accepted(client, name):
    body = {"name": name, "payload": {}, "session_id": "s1", "component": "BookingForm"}
    response = client.post("/v1/action", json=body)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unknown_action_is_422_with_errors(client):
    body = {"name": "drop_tables", "payload": {}, "session_id": "s1", "component": "X"}
    response = client.post("/v1/action", json=body)
    assert response.status_code == 422
    assert response.json()["ok"] is False
    assert response.json()["errors"][0]["field"] == "name"


def test_healthz_is_200_with_database_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "database", "model", "embedder", "graph_version"}
    assert body["database"] == "ok"
    assert body["status"] in ("ok", "degraded")
    assert body["model"] in ("ok", "down")


def test_cors_allows_a_configured_origin(client, settings):
    origin = settings.allowed_origins[0]
    response = client.get("/v1/metrics", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_refuses_an_unknown_origin(client):
    response = client.get("/v1/metrics", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
    preflight = client.options(
        "/v1/intent",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_bootstrap_serves_the_business(client):
    response = client.get("/v1/bootstrap")
    if response.status_code == 503:
        assert response.json() == {"detail": "graph not published"}
        pytest.skip("graph not seeded")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"business", "theme", "nav", "chips"}
    assert body["business"]["name"] == "The Kenmore"
    assert body["business"]["tagline"]
    if not body["nav"]:
        pytest.skip("seed has no nav/chips on the Business node yet")
    assert len(body["nav"]) == 4
    assert all(set(entry) == {"label", "preset"} for entry in body["nav"])
    assert len(body["chips"]) == 3
