"""The owner's inbox: an HTML page and the same data as JSON (SCHEMA 8.6, O4)."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app import auth
from app.infra.db import get_conn
from app.services import inbox
from app.web.inbox_page import render

router = APIRouter(prefix="/owner", tags=["inbox"])
PAGE_CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"
            " connect-src 'self'; base-uri 'none'; form-action 'none'")


@router.get("/inbox.json", dependencies=[Depends(auth.require_owner)])
def inbox_json(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    return inbox.build(conn, request.app.state.settings.business_id)


@router.get("/inbox", response_class=HTMLResponse)
def inbox_page(request: Request, token: str | None = None,
               conn: psycopg.Connection = Depends(get_conn)) -> Response:
    settings = request.app.state.settings
    if token is not None:
        if not auth.matches(token, settings.owner_inbox_token):
            raise HTTPException(401, "unknown token")
        redirect = RedirectResponse("/owner/inbox", status_code=303)
        redirect.set_cookie(auth.COOKIE, token, httponly=True, samesite="strict",
                            max_age=60 * 60 * 12)
        return redirect
    auth.require_owner(auth.principal(request))
    page = render(inbox.build(conn, settings.business_id))
    return HTMLResponse(page, headers={"Content-Security-Policy": PAGE_CSP,
                                       "Cache-Control": "no-store"})
