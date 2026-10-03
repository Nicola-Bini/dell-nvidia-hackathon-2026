"""Credentials: the agent token is refused on owner-only routes."""

import pytest
from fastapi.testclient import TestClient

from app.infra.common_shim import Settings
from app.main import create_app

AGENT = {"Authorization": "Bearer agent-secret"}
OWNER = {"Authorization": "Bearer owner-secret"}


def make_settings(**kw) -> Settings:
    base = dict(business_id="biz_demo", tz="America/New_York", owner_database_url="",
                embed_base_url="", embed_model="m", embed_dim=1024,
                serve_base_url="http://127.0.0.1:1", owner_tools_token="agent-secret",
                owner_inbox_token="owner-secret", owner_channel_user_id="owner",
                autonomy="balanced", gap_ask_min_sessions=1)
    base.update(kw)
    return Settings(**base)


@pytest.fixture()
def client():
    return TestClient(create_app(make_settings()))


def test_healthz_needs_no_token(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["service"] == "owner"


@pytest.mark.parametrize("action", ["approve", "reject", "revert"])
def test_agent_token_refused_on_owner_only_route(client, action):
    r = client.post(f"/owner/changes/1/{action}" if action == "approve"
                    else f"/owner/changes/1/{action}", headers=AGENT)
    assert r.status_code == 403
    assert r.json()["detail"]["tier"] == "locked"


def test_no_token_is_401(client):
    assert client.post("/owner/changes/1/approve").status_code == 401


def test_wrong_token_is_401(client):
    r = client.post("/owner/changes/1/approve", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_owner_token_passes_auth(client):
    r = client.post("/owner/changes/1/approve", headers=OWNER)
    assert r.status_code != 403 and r.status_code != 401


def test_empty_configured_tokens_never_match():
    c = TestClient(create_app(make_settings(owner_tools_token="", owner_inbox_token="")))
    assert c.post("/owner/changes/1/approve",
                  headers={"Authorization": "Bearer "}).status_code == 401
