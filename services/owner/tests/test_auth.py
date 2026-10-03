"""Credentials: the agent token is refused on owner-only routes."""

import pytest
from fastapi.testclient import TestClient

from cac_common.settings import Settings, load_settings
from app.main import create_app

AGENT = {"Authorization": "Bearer agent-secret"}
OWNER = {"Authorization": "Bearer owner-secret"}


def make_settings(**kw) -> Settings:
    env = {"OWNER_TOOLS_TOKEN": "agent-secret", "OWNER_INBOX_TOKEN": "owner-secret"}
    env.update({k.upper(): v for k, v in kw.items()})
    return load_settings(env)


@pytest.fixture()
def bare():
    """No database behind it: for tests that must be decided before any query."""
    return TestClient(create_app(make_settings()))


def test_healthz_needs_no_token(bare):
    r = bare.get("/healthz")
    assert r.status_code == 200 and r.json()["service"] == "owner"


@pytest.mark.parametrize("action", ["approve", "reject", "revert"])
def test_agent_token_refused_on_owner_only_route(bare, action):
    r = bare.post(f"/owner/changes/1/{action}", headers=AGENT)
    assert r.status_code == 403
    assert r.json()["detail"]["tier"] == "locked"


def test_no_token_is_401(bare):
    assert bare.post("/owner/changes/1/approve").status_code == 401


def test_wrong_token_is_401(bare):
    r = bare.post("/owner/changes/1/approve", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_owner_token_passes_auth(client):
    r = client.post("/owner/changes/1/approve", headers=OWNER)
    assert r.status_code == 404  # authorised; there is just no change 1


def test_empty_configured_tokens_never_match():
    c = TestClient(create_app(make_settings(owner_tools_token="", owner_inbox_token="")))
    assert c.post("/owner/changes/1/approve",
                  headers={"Authorization": "Bearer "}).status_code == 401
