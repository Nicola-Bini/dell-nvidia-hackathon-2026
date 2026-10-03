"""Locates the widget, embed script and demo site on disk, on every request.

Nothing is cached: the widget may be built while the server is running.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROOTS = {
    "widget": Path("apps") / "widget" / "dist",
    "site": Path("apps") / "demo-site" / "dist",
}


def repo_root() -> Path:
    """The repository root, or `CAC_REPO_ROOT` when set."""
    override = os.environ.get("CAC_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[5]


def resolve(kind: str, relative: str) -> Path | None:
    """The file for `relative` under the `kind` build, or None (missing, or outside it)."""
    base = (repo_root() / _ROOTS[kind]).resolve()
    if not base.is_dir() or "\x00" in relative:
        return None
    target = (base / relative.lstrip("/")).resolve() if relative else base
    if target != base and not target.is_relative_to(base):
        return None
    if target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None
