"""The Serve API (SCHEMA 8.5). Run: `uv run uvicorn cac_serve.main:app --port 8080`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from cac_common.settings import Settings, get_settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout

from cac_serve.infra import db
from cac_serve.infra.startup_checks import assert_local
from cac_serve.routes import health, static, v1
from cac_serve.services.pipeline import GraphNotPublished


def _assert_models_are_local(settings: Settings) -> None:
    assert_local(settings.llm_base_url, "LLM_BASE_URL")
    if settings.embed_base_url:
        assert_local(settings.embed_base_url, "EMBED_BASE_URL")


def _database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


def _graph_not_published(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "graph not published"})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Raises RuntimeError when a model endpoint is not on this machine."""
    settings = settings or get_settings()
    _assert_models_are_local(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.open_pool(settings.serve_database_url, min_size=1, max_size=8)
        try:
            yield
        finally:
            db.close_pool()

    app = FastAPI(title="CAC Serve API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(psycopg.Error, _database_unavailable)
    app.add_exception_handler(PoolTimeout, _database_unavailable)
    app.add_exception_handler(GraphNotPublished, _graph_not_published)
    app.include_router(v1.router)
    app.include_router(health.router)
    app.include_router(static.router)
    return app


app = create_app()
