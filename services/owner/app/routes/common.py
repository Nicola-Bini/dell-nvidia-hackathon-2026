"""Helpers every route shares: answering with ChangeError statuses, and the post-publish
pre-warm that must start only after the publish has been committed."""

from collections.abc import Callable

import psycopg
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from app.domain.requests import ChangeError
from app.services import prewarm


def respond(request: Request, conn: psycopg.Connection, payload: dict,
            status: int = 200) -> JSONResponse:
    """JSON answer. When `payload` carries a `graph_version` a publish happened: commit it,
    then replay the top intents in the background so the cache is warm."""
    background = None
    if payload.get("graph_version") is not None:
        conn.commit()
        settings, transport = request.app.state.settings, request.app.state.serve_transport
        summary, texts = prewarm.plan(conn, settings, transport)
        payload = {**payload, "prewarm": summary}
        if texts:
            background = BackgroundTask(prewarm.run, texts, settings.serve_base_url.rstrip("/"),
                                        transport)
    return JSONResponse(payload, status_code=status, background=background)


def run(request: Request, conn: psycopg.Connection, call: Callable[[], dict]) -> JSONResponse:
    """Run a service call; a ChangeError becomes its HTTP status with the transaction undone."""
    try:
        payload = call()
    except ChangeError as err:
        conn.rollback()
        return JSONResponse({"detail": err.message}, status_code=err.status)
    return respond(request, conn, payload)
