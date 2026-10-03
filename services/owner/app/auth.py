"""Two credentials (SCHEMA 8.6): the agent's tools token and the owner's inbox token.

The agent sends `Authorization: Bearer`. The owner's browser cannot set headers on a page
load, so `GET /owner/inbox?token=` swaps the inbox token for an HttpOnly, SameSite=Strict
cookie. A cookie-authenticated write must also carry `X-Requested-With: cac-inbox`, which a
cross-site form cannot add.
"""

import hmac
from typing import Literal

from fastapi import Depends, HTTPException, Request

Principal = Literal["agent", "owner"]
COOKIE = "cac_inbox"
CSRF_HEADER = ("x-requested-with", "cac-inbox")
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def matches(presented: str, expected: str) -> bool:
    return bool(presented and expected) and hmac.compare_digest(presented, expected)


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


def principal(request: Request) -> Principal:
    settings = request.app.state.settings
    bearer = _bearer(request)
    if matches(bearer, settings.owner_inbox_token):
        return "owner"
    if matches(bearer, settings.owner_tools_token):
        return "agent"
    cookie = request.cookies.get(COOKIE, "")
    if not bearer and matches(cookie, settings.owner_inbox_token):
        if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER[0]) \
                != CSRF_HEADER[1]:
            raise HTTPException(status_code=403, detail="missing X-Requested-With header")
        return "owner"
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


def require_agent(who: Principal = Depends(principal)) -> Principal:
    if who != "agent":
        raise HTTPException(
            status_code=403,
            detail={"tier": "locked",
                    "reason": "Changes are submitted with the agent's tools token. The "
                              "owner decides through the inbox, not through this route."})
    return who
