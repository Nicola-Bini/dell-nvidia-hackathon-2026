"""Shared pieces of the binder: the bound-view record and catalog lookups."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cac_serve.domain import templates
from cac_serve.domain.graph import Graph, Node

FORM_CARD = "FormCard"


@dataclass
class BoundView:
    """One view of a Surface before ids are assigned, with the catalog entry behind it."""

    component: str
    data: dict
    text: str
    actions: list[dict] = field(default_factory=list)
    entry: Node | None = None
    say: str | None = None  # a computed sentence that replaces the catalog `say`


def action(name: str, handler: str) -> dict:
    return {"name": name, "handler": handler}


def form_entry(graph: Graph, form_id: Any) -> Node | None:
    """A configured form: a catalog entry with primitive == "FormCard"."""
    node = graph.get(form_id) if isinstance(form_id, str) else None
    if node is None or node.label != "UIComponent" or node.props.get("primitive") != FORM_CARD:
        return None
    return node


def entry_for(graph: Graph, view: dict) -> Node | None:
    """The catalog entry behind a selected view; None when it is not in the catalog."""
    component = view.get("component")
    if not isinstance(component, str):
        return None
    if component == FORM_CARD:
        return form_entry(graph, view.get("form"))
    return graph.component(component)


def business_name(graph: Graph) -> str:
    business = graph.business()
    return business.name if business is not None and business.name else templates.FALLBACK_BUSINESS


def service(graph: Graph, kind: str) -> Node | None:
    """The published Service of one kind (reservations, catering), lowest id first."""
    found = [n for n in graph.by_label("Service") if n.props.get("kind") == kind]
    return min(found, key=lambda n: n.id) if found else None


def facts(node: Node) -> list[dict]:
    """A node's public props as labelled facts, in stored order, skipping empty values."""
    rows = []
    for key, value in node.props.items():
        text = templates.fact_value(value)
        if text:
            rows.append({"name": templates.plain_words(key), "value": text})
    return rows
