"""Channel comes from the caller, never the body; the header counts only from loopback."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from cac_serve.infra.channel import resolve_channel


def _request(client_host: str | None, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {"type": "http", "method": "POST", "path": "/v1/intent", "headers": raw,
             "client": (client_host, 5555) if client_host else None}
    return Request(scope)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "127.0.0.2"])
@pytest.mark.parametrize("channel", ["mcp", "prewarm"])
def test_header_is_honoured_from_loopback(host, channel):
    assert resolve_channel(_request(host, {"X-CAC-Channel": channel})) == channel


@pytest.mark.parametrize("host", ["203.0.113.9", "192.168.1.50", "testclient", None])
def test_header_is_ignored_from_a_non_loopback_client(host):
    assert resolve_channel(_request(host, {"X-CAC-Channel": "mcp"})) == "web"


def test_unknown_header_value_is_web():
    assert resolve_channel(_request("127.0.0.1", {"X-CAC-Channel": "owner"})) == "web"


def test_no_header_is_web():
    assert resolve_channel(_request("127.0.0.1")) == "web"


def test_proxied_request_is_web_even_from_loopback():
    headers = {"X-CAC-Channel": "mcp", "X-Forwarded-For": "203.0.113.9"}
    assert resolve_channel(_request("127.0.0.1", headers)) == "web"


def test_channel_in_the_body_is_ignored(client, monkeypatch):
    seen = {}

    def fake_handle(text, session_id, channel, context=None):
        seen["channel"] = channel
        return {"ok": True}

    monkeypatch.setattr("cac_serve.routes.v1.handle_intent", fake_handle)
    body = {"text": "hi", "session_id": "s1", "channel": "mcp"}
    response = client.post("/v1/intent", json=body, headers={"X-CAC-Channel": "mcp"})
    assert response.status_code == 200
    assert seen["channel"] == "web"
