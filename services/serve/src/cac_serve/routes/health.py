"""GET /healthz: always HTTP 200; the body says what is up."""

from __future__ import annotations

from fastapi import APIRouter, Request

from cac_serve.services.health_service import check_health

router = APIRouter()


@router.get("/healthz")
def healthz(request: Request) -> dict:
    return check_health(request.app.state.settings)
