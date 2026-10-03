"""What the agent can read (SCHEMA 8.6). Locked labels by name only; no leads or visitor text."""

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import require_any
from app.infra import reads
from app.infra.db import get_conn

router = APIRouter(prefix="/owner", tags=["read"], dependencies=[Depends(require_any)])
State = Literal["pending", "applied", "rejected", "reverted"]


def _biz(request: Request) -> str:
    return request.app.state.settings.business_id


@router.get("/schema")
def schema(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    return {"labels": reads.labels(conn), "edge_types": reads.edge_types(conn),
            "catalog": reads.catalog(conn, _biz(request))}


@router.get("/graph/search")
def graph_search(request: Request, q: str = Query("", max_length=200),
                 label: str | None = Query(None, max_length=60),
                 conn: psycopg.Connection = Depends(get_conn)) -> dict:
    if label and reads.is_locked_label(conn, label):
        raise HTTPException(403, detail={"tier": "locked",
                                         "reason": f"{label} is a locked label: not readable."})
    nodes = reads.search_nodes(conn, _biz(request), q.strip(), label)
    return {"nodes": nodes, "edges": reads.edges_among_readable(conn, [n["id"] for n in nodes])}


@router.get("/changes")
def changes(request: Request, state: State | None = None,
            conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    return reads.agent_changes(conn, _biz(request), state)


@router.get("/digest")
def digest(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    return reads.digest(conn, _biz(request), request.app.state.settings.tz)
