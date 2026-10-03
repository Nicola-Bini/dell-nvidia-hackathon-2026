"""Request shape for POST /owner/changes and the validators every action shares."""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.compat import normalize
from app.domain.tiers import ACTIONS

ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
LABEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]{1,39}$")
EDGE_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,39}$")
PROP_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_AFTER_BYTES = 16_000
PRIMITIVES = ("FormCard", "FactCard", "ListCard")
FIELD_TYPES = ("text", "number", "date", "select")
CATALOG_KEYS = ("component", "version", "use_when", "binds", "selectable", "preset", "cta_label",
                "rail_label", "say", "chips", "channels", "primitive", "fields", "submit_label")

Action = Literal[ACTIONS]  # type: ignore[valid-type]


class ChangeRequest(BaseModel):
    action: Action
    target: str = Field(min_length=1, max_length=200)
    after: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=500)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _accept_client_shapes(cls, raw: Any) -> Any:
        return normalize(raw)

    @field_validator("after", "evidence")
    @classmethod
    def _small(cls, value: dict) -> dict:
        if len(json.dumps(value)) > MAX_AFTER_BYTES:
            raise ValueError("payload too large")
        return value

    @field_validator("reason")
    @classmethod
    def _reason_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a reason is required: the owner reads it")
        return value.strip()


class ChangeError(Exception):
    """A request the engine cannot apply. `status` is the HTTP status to answer with."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def check_id(value: str, what: str = "id") -> str:
    if not ID_RE.match(value):
        raise ChangeError(422, f"{what} {value!r} must match {ID_RE.pattern}")
    return value


def check_props(props: Any) -> dict:
    if props is None:
        return {}
    if not isinstance(props, dict) or not all(isinstance(k, str) for k in props):
        raise ChangeError(422, "props must be an object")
    return props


def prop_names(after: dict) -> list[str]:
    raw = after.get("props") or after.get("public_props") or after.get("prop")
    names = [raw] if isinstance(raw, str) else list(raw or [])
    bad = [n for n in names if not isinstance(n, str) or not PROP_RE.match(n)]
    if bad or not names:
        raise ChangeError(422, f"prop names must match {PROP_RE.pattern}: {bad or 'none given'}")
    return names


def validate_form_fields(fields: Any) -> list[dict]:
    if not isinstance(fields, list) or not fields:
        raise ChangeError(422, "a FormCard needs a non-empty fields list")
    for f in fields:
        ok = (isinstance(f, dict) and PROP_RE.match(str(f.get("name", "")))
              and f.get("type") in FIELD_TYPES and str(f.get("label", "")).strip())
        if not ok:
            raise ChangeError(422, "each field needs name, label and a type of "
                                   + ", ".join(FIELD_TYPES))
    return fields


def catalog_entry(after: dict, existing: dict | None = None) -> dict:
    """Validate a catalog entry (SCHEMA 7) and fill every key, null when unused."""
    entry = {**(existing or {}), **{k: v for k, v in after.items() if k in CATALOG_KEYS}}
    if not str(entry.get("component", "")).strip() or not str(entry.get("use_when", "")).strip():
        raise ChangeError(422, "an element needs a component name and a use_when line")
    if entry.get("primitive") not in PRIMITIVES:
        raise ChangeError(422, f"agent elements are built on {', '.join(PRIMITIVES)}")
    if entry["primitive"] == "FormCard":
        validate_form_fields(entry.get("fields"))
    defaults = {"version": 1, "selectable": True, "channels": ["web", "mcp"]}
    return {k: entry.get(k, defaults.get(k)) for k in CATALOG_KEYS}
