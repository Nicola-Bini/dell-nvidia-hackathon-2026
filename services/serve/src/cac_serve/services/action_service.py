"""POST /v1/action: the three server-handled submits (SCHEMA 7 and 8.5). Never calls the model.

Payloads are untrusted: every field is validated and every referenced id is re-checked in
kg_public before a lead is stored. Lead details go to ops.lead and nowhere else.
"""

from __future__ import annotations

from typing import Any

from cac_common.settings import get_settings

from cac_serve.domain import action_rules
from cac_serve.domain.confirm import confirmation_surface
from cac_serve.domain.graph import Graph, Node
from cac_serve.infra import db, lead_repo
from cac_serve.infra.graph_repo import load_graph
from cac_serve.infra.metrics import metrics
from cac_serve.infra.rate_limit import lead_limiter
from cac_serve.services.pipeline import GraphNotPublished, business_today

SUBMIT_ACTIONS = frozenset({"submit_booking_request", "submit_catering_quote", "submit_form"})
LEAD_CHANNELS = frozenset({"web", "mcp", "a2a"})
TOO_MANY = "Too many requests. Please call us instead."


class ActionRejected(Exception):
    """A failed submit: `{ ok: false, errors: [{ field, message }] }` (SCHEMA 8.4)."""

    def __init__(self, errors: list[dict[str, str]], status_code: int = 422) -> None:
        super().__init__("action rejected")
        self.errors = errors
        self.status_code = status_code


def _reject(field: str, message: str) -> ActionRejected:
    return ActionRejected([{"field": field, "message": message}])


def _service(graph: Graph, kind: str) -> Node:
    for node in graph.by_label("Service"):
        if node.props.get("kind") == kind:
            return node
    raise _reject("name", "This request is not available.")


def _form(graph: Graph, payload: dict[str, Any]) -> Node:
    form_id = payload.get("form")
    for node in graph.forms():
        if node.id == form_id:
            return node
    raise _reject("form", "Unknown form.")


def _validate(graph: Graph, name: str, payload: dict[str, Any]) -> tuple[str, str, dict, list]:
    """Returns (lead kind, component, clean payload, errors) for a known submit."""
    today = business_today(get_settings())
    if name == "submit_booking_request":
        _service(graph, "reservations")
        clean, errors = action_rules.validate_booking(payload, today)
        return "booking_request", "BookingForm", clean, errors
    if name == "submit_catering_quote":
        minimum = _service(graph, "catering").props.get("min_headcount")
        clean, errors = action_rules.validate_catering(payload, today, minimum)
        return "catering_quote", "CateringQuoteForm", clean, errors
    form = _form(graph, payload)
    clean, errors = action_rules.validate_form(form, payload, today)
    return "form", form.id, clean, errors


def handle_action(
    name: str, payload: dict[str, Any], session_id: str, component: str | None, channel: str
) -> dict:
    """Run one server-handled action. `component` from the body is ignored: the stored
    component is derived from the action and the form id, never trusted from the client."""
    if name not in SUBMIT_ACTIONS:
        raise _reject("name", "unknown action")
    settings = get_settings()
    with db.snapshot() as conn:
        graph = load_graph(conn, settings.business_id)
    if graph.version == 0:
        raise GraphNotPublished()
    kind, stored_component, clean, errors = _validate(graph, name, payload)
    if errors:
        raise ActionRejected(errors)
    if not lead_limiter.try_acquire(session_id, channel):
        raise ActionRejected([{"field": "", "message": TOO_MANY}], status_code=429)
    lead = lead_repo.Lead(
        business_id=settings.business_id, kind=kind, component=stored_component,
        payload=clean, channel=channel if channel in LEAD_CHANNELS else "web",
        session_id=session_id,
    )
    with db.writer() as conn:
        lead_id = lead_repo.insert(conn, lead)
    metrics.incr_leads()
    return {"ok": True, "lead_id": str(lead_id), "surface": confirmation_surface(graph)}
