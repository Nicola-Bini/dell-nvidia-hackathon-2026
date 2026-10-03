"""Golden surfaces from fixtures/surfaces, used by the stub services until the pipeline lands."""

from __future__ import annotations

import json
from pathlib import Path

from cac_serve.infra.static_files import repo_root


def _surfaces_dir() -> Path:
    return repo_root() / "fixtures" / "surfaces"


def load_golden(name: str) -> dict:
    """A golden Surface by file stem, e.g. `load_golden("off_topic")`."""
    return json.loads((_surfaces_dir() / f"{name}.json").read_text(encoding="utf-8"))


def load_index() -> dict[str, str]:
    """Intent text (exact) -> golden file name."""
    return json.loads((_surfaces_dir() / "index.json").read_text(encoding="utf-8"))
