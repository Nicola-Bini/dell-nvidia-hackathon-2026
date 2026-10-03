"""Request helpers shared by the end-to-end tests."""

from __future__ import annotations

import httpx


def ask(serve: httpx.Client, text: str, session_id: str, headers: dict | None = None) -> dict:
    response = serve.post("/v1/intent", json={"text": text, "session_id": session_id},
                          headers=headers or {})
    assert response.status_code == 200, response.status_code
    return response.json()


def components(surface: dict) -> list[str]:
    return [view["component"] for view in surface["views"]]
