"""The /v1 endpoints (SCHEMA 8.5). Routes validate and delegate; logic lives in services."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cac_serve.infra.channel import resolve_channel
from cac_serve.infra.metrics import metrics
from cac_serve.services.action_service import ActionRejected, handle_action
from cac_serve.services.bootstrap_service import get_bootstrap
from cac_serve.services.intent_service import InvalidText, clean_text, handle_intent
from cac_serve.services.metrics_service import get_metrics
from cac_serve.services.preset_service import get_preset

router = APIRouter(prefix="/v1")


class IntentBody(BaseModel):
    text: str
    session_id: str = Field(min_length=1, max_length=128)
    context: dict[str, Any] | None = None


class ActionBody(BaseModel):
    name: str = Field(max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str = Field(min_length=1, max_length=128)
    component: str | None = Field(default=None, max_length=64)


@router.get("/bootstrap")
def bootstrap(request: Request) -> dict:
    payload = get_bootstrap(request.app.state.settings.business_id)
    if payload is None:
        raise HTTPException(status_code=503, detail="graph not published")
    return payload


@router.post("/intent")
def intent(body: IntentBody, request: Request) -> dict:
    started = time.perf_counter()
    try:
        text = clean_text(body.text, request.app.state.settings.intent_max_chars)
    except InvalidText as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    surface = handle_intent(text, body.session_id, resolve_channel(request), body.context)
    metrics.record_latency((time.perf_counter() - started) * 1000)
    return surface


@router.get("/view/{preset}")
def view(preset: str, src: str | None = None) -> dict:
    surface = get_preset(preset, src)
    if surface is None:
        raise HTTPException(status_code=404, detail="unknown preset")
    return surface


@router.post("/action", response_model=None)
def action(body: ActionBody, request: Request) -> dict | JSONResponse:
    channel = resolve_channel(request)
    try:
        return handle_action(body.name, body.payload, body.session_id, body.component, channel)
    except ActionRejected as exc:
        return JSONResponse(status_code=422, content={"ok": False, "errors": exc.errors})


@router.get("/metrics")
def metrics_view(request: Request) -> dict:
    return get_metrics(request.app.state.settings)
