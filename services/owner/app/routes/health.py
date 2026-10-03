"""Liveness for the start order (SCHEMA section 2)."""

import psycopg
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/healthz", tags=["health"])
def healthz(request: Request) -> dict:
    url = request.app.state.settings.owner_database_url
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except psycopg.Error:
        db = "down"
    return {"ok": True, "service": "owner", "db": db}
