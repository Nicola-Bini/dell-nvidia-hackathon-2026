"""The widget, the embed script and the demo site, straight from their build folders."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from cac_serve.infra import static_files

router = APIRouter()
_NO_CACHE = {"Cache-Control": "no-cache"}


def _serve(kind: str, relative: str) -> FileResponse:
    path = static_files.resolve(kind, relative)
    if path is None:
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, headers=_NO_CACHE)


@router.get("/embed.js", include_in_schema=False)
def embed_js() -> FileResponse:
    return _serve("widget", "embed.js")


@router.get("/widget/", include_in_schema=False)
def widget_index() -> FileResponse:
    return _serve("widget", "")


@router.get("/widget/{path:path}", include_in_schema=False)
def widget_file(path: str) -> FileResponse:
    return _serve("widget", path)


@router.get("/site/", include_in_schema=False)
def site_index() -> FileResponse:
    return _serve("site", "")


@router.get("/site/{path:path}", include_in_schema=False)
def site_file(path: str) -> FileResponse:
    return _serve("site", path)
