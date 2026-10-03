"""Two credentials (SCHEMA 8.6): the agent's tools token and the owner's inbox token."""

import hmac
from typing import Literal

from fastapi import Depends, HTTPException, Request

Principal = Literal["agent", "owner"]


def _presented_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    # The inbox page is opened in a browser: accept ?token= or the cookie it sets.
    return request.query_params.get("token") or request.cookies.get("cac_inbox", "")


def principal(request: Request) -> Principal:
    settings = request.app.state.settings
    token = _presented_token(request)
    if token and settings.owner_inbox_token and hmac.compare_digest(
            token, settings.owner_inbox_token):
        return "owner"
    if token and settings.owner_tools_token and hmac.compare_digest(
            token, settings.owner_tools_token):
        return "agent"
    raise HTTPException(status_code=401, detail="missing or unknown bearer token")


def require_any(who: Principal = Depends(principal)) -> Principal:
    return who


def require_owner(who: Principal = Depends(principal)) -> Principal:
    if who != "owner":
        raise HTTPException(
            status_code=403,
            detail={"tier": "locked",
                    "reason": "Only the owner's inbox credential can do this. "
                              "The agent cannot approve, reject, revert or verify."})
    return who
