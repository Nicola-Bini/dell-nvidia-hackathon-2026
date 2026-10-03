"""Routes only the owner's inbox credential may call (SCHEMA 8.6)."""

import psycopg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import require_owner
from app.domain.requests import ChangeError
from app.infra.db import get_conn
from app.services import decisions

router = APIRouter(prefix="/owner", tags=["owner only"], dependencies=[Depends(require_owner)])


class Rejection(BaseModel):
    reason: str | None = Field(None, max_length=500)


class VerifyRequest(BaseModel):
    node_ids: list[str] = Field(default_factory=list, max_length=200)
    edge_ids: list[int] = Field(default_factory=list, max_length=200)


def _run(conn: psycopg.Connection, call) -> JSONResponse:
    try:
        return JSONResponse(call())
    except ChangeError as err:
        conn.rollback()
        return JSONResponse({"detail": err.message}, status_code=err.status)


@router.post("/changes/{change_id}/approve")
def approve(change_id: int, request: Request,
            conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Publish a pending change."""
    return _run(conn, lambda: decisions.approve(conn, request.app.state.settings, change_id))


@router.post("/changes/{change_id}/reject")
def reject(change_id: int, request: Request, body: Rejection | None = None,
           conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Discard a pending change. The agent sees the rejection and its reason."""
    reason = body.reason if body else None
    return _run(conn, lambda: decisions.reject(conn, request.app.state.settings, change_id,
                                               reason))


@router.post("/changes/{change_id}/revert")
def revert(change_id: int, request: Request,
           conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Restore `before`, publish, and mark the change reverted."""
    return _run(conn, lambda: decisions.revert(conn, request.app.state.settings, change_id))


@router.post("/verify")
def verify(body: VerifyRequest, request: Request,
           conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Set verified_by_owner on nodes or edges: the only path to a verified badge."""
    return _run(conn, lambda: decisions.verify(conn, request.app.state.settings,
                                               body.node_ids, body.edge_ids))
