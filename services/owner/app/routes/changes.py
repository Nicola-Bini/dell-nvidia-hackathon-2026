"""POST /owner/changes: the agent's one write endpoint (SCHEMA 8.6)."""

import psycopg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth import require_agent
from app.domain.requests import ChangeError, ChangeRequest
from app.infra.db import get_conn
from app.services import change_engine

router = APIRouter(prefix="/owner", tags=["agent writes"], dependencies=[Depends(require_agent)])


@router.post("/changes", responses={403: {"description": "Locked tier: refused, with the reason"}})
def post_change(req: ChangeRequest, request: Request,
                conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Apply a change. The API assigns the tier; the agent cannot choose it."""
    try:
        result = change_engine.submit(conn, request.app.state.settings, req)
    except ChangeError as err:
        conn.rollback()
        return JSONResponse({"detail": err.message}, status_code=err.status)
    return JSONResponse(result.body(), status_code=403 if result.tier == "locked" else 200)
