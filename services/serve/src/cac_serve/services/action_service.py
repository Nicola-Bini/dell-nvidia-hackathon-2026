"""POST /v1/action. STUB (wp2): known submits are accepted; validation and the lead insert
land in wp5."""

from __future__ import annotations

from typing import Any

SUBMIT_ACTIONS = frozenset({"submit_booking_request", "submit_catering_quote", "submit_form"})


class ActionRejected(Exception):
    """A failed submit: HTTP 422 `{ ok: false, errors: [{ field, message }] }` (SCHEMA 8.4)."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("action rejected")
        self.errors = errors


def handle_action(
    name: str, payload: dict[str, Any], session_id: str, component: str | None, channel: str
) -> dict:
    """Run one server-handled action and return `{ "ok": true, "surface"? }`."""
    if name not in SUBMIT_ACTIONS:
        raise ActionRejected([{"field": "name", "message": "unknown action"}])
    return {"ok": True}
