"""Binder rule 1 (SCHEMA 8.3): validate and clean the model's selection before binding.

A view is rejected when its component is not an approved selectable catalog entry, when it
names an id that was not a retrieved candidate, or when a node's label does not match the
entry's `binds.labels` ([] means any label). Cleaning de-duplicates ids, keeps the first
view per component and caps the surface at two views.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cac_serve.domain.bind_core import FORM_CARD, entry_for
from cac_serve.domain.graph import Graph, Node

MAX_VIEWS = 2
MAX_TOPIC = 60
_NO_ID_COMPONENTS = ("HoursCard", "BookingForm", "CateringQuoteForm")
_NO_CARD_LABELS = ("UIComponent",)


@dataclass(frozen=True)
class _Ctx:
    graph: Graph
    candidates: frozenset[str]


def _shown(value: Any) -> str:
    return repr(value)[:60]


def _id_error(ctx: _Ctx, node_id: Any, labels: list[str], field: str) -> str | None:
    """Why this id cannot be bound, or None when it can."""
    if not isinstance(node_id, str) or node_id not in ctx.candidates:
        return f"{field} {_shown(node_id)} was not a candidate"
    node = ctx.graph.get(node_id)
    if node is None:
        return f"{field} {_shown(node_id)} is not in the published graph"
    if labels and node.label not in labels:
        return f"{field} {_shown(node_id)} has label {node.label}, expected {' or '.join(labels)}"
    if node.label in _NO_CARD_LABELS:
        return f"{field} {_shown(node_id)} is a catalog entry, not data"
    return None


def _bind_labels(entry: Node) -> list[str]:
    binds = entry.props.get("binds")
    labels = binds.get("labels") if isinstance(binds, dict) else None
    return [str(label) for label in labels] if isinstance(labels, list) else []


def _dedupe(values: Any) -> list:
    return list(dict.fromkeys(values)) if isinstance(values, list) else []


def _optional_id(ctx: _Ctx, view: dict, field: str, label: str) -> tuple[Any, list[str]]:
    value = view.get(field)
    if value is None:
        return None, []
    error = _id_error(ctx, value, [label], f"MenuList.{field}")
    return (None, [error]) if error else (value, [])


def _clean_menu(ctx: _Ctx, view: dict, entry: Node) -> tuple[dict, list[str]]:
    diet, errors = _optional_id(ctx, view, "diet", "Diet")
    section, section_errors = _optional_id(ctx, view, "section", "MenuSection")
    errors += section_errors
    items = []
    for item_id in _dedupe(view.get("items")):
        error = _id_error(ctx, item_id, _bind_labels(entry), "MenuList.items")
        if error:
            errors.append(error)
        else:
            items.append(item_id)
    if not errors and diet is None and section is None and not items:
        errors.append("MenuList needs a diet, a section or named items; if the data has no "
                      "line for what was asked, reply with kind gap")
    clean = {"component": "MenuList", "diet": diet, "section": section, "items": items,
             "order": view.get("order") is True}
    return clean, errors


def _clean_single(ctx: _Ctx, view: dict, entry: Node, field: str) -> tuple[dict, list[str]]:
    component = view["component"]
    error = _id_error(ctx, view.get(field), _bind_labels(entry), f"{component}.{field}")
    return {"component": component, field: view.get(field)}, [error] if error else []


def _clean_allergen(ctx: _Ctx, view: dict, entry: Node) -> tuple[dict, list[str]]:
    """Allergen[0..1]: no allergen is the notice alone; a named one must be a candidate."""
    if view.get("allergen") is None:
        return {"component": "AllergenNotice", "allergen": None}, []
    return _clean_single(ctx, view, entry, "allergen")


def _clean_list_card(ctx: _Ctx, view: dict, _entry: Node) -> tuple[dict, list[str]]:
    label = view.get("label")
    labels = {n.label for n in map(ctx.graph.get, ctx.candidates) if n is not None}
    errors = []
    if not isinstance(label, str) or label not in labels or label in _NO_CARD_LABELS:
        errors.append(f"ListCard.label {_shown(label)} is not the label of a candidate")
    return {"component": "ListCard", "label": label}, errors


def _clean_view(ctx: _Ctx, view: dict, entry: Node) -> tuple[dict, list[str]]:
    component = view["component"]
    if component == "MenuList":
        return _clean_menu(ctx, view, entry)
    if component == "Answer":
        return _clean_single(ctx, view, entry, "faq")
    if component == "AllergenNotice":
        return _clean_allergen(ctx, view, entry)
    if component == "FactCard":
        return _clean_single(ctx, view, entry, "node")
    if component == "ListCard":
        return _clean_list_card(ctx, view, entry)
    if component == FORM_CARD:
        return {"component": FORM_CARD, "form": entry.id}, []
    if component in _NO_ID_COMPONENTS:
        return {"component": component}, []
    return {}, [f"component {_shown(component)} cannot be bound"]


def _approved_entry(graph: Graph, view: Any) -> tuple[Node | None, str | None]:
    """The approved, selectable catalog entry behind a view, or the reason there is none."""
    if not isinstance(view, dict):
        return None, "a view must be an object"
    entry = entry_for(graph, view)
    name = view.get("form") if view.get("component") == FORM_CARD else view.get("component")
    if entry is None:
        return None, f"component {_shown(name)} is not an approved catalog entry"
    if entry.props.get("selectable") is False:
        return None, f"component {_shown(name)} is not selectable"
    return entry, None


def _clean_views(ctx: _Ctx, views: Any) -> tuple[list[dict], list[str]]:
    cleaned: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for view in views if isinstance(views, list) else []:
        entry, error = _approved_entry(ctx.graph, view)
        if entry is None:
            errors.append(error or "invalid view")
            continue
        if view["component"] in seen:
            continue  # keep the first view per component
        seen.add(view["component"])
        clean, view_errors = _clean_view(ctx, view, entry)
        errors += view_errors
        if not view_errors:
            cleaned.append(clean)
    return cleaned[:MAX_VIEWS], errors


def clean_selection(
    graph: Graph, candidate_ids: list[str], selection: dict
) -> tuple[dict, list[str]]:
    """Rule 1. Returns (cleaned selection, errors); any error means "retry the model"."""
    kind = selection.get("kind") if isinstance(selection, dict) else None
    if kind == "off_topic":
        return {"kind": "off_topic"}, []
    if kind == "gap":
        topic = selection.get("topic")
        return {"kind": "gap", "topic": topic[:MAX_TOPIC] if isinstance(topic, str) else ""}, []
    if kind != "answer":
        return {"kind": "gap", "topic": ""}, [f"unknown kind {_shown(kind)}"]
    views, errors = _clean_views(_Ctx(graph, frozenset(candidate_ids)), selection.get("views"))
    if not views and not errors:
        errors.append("an answer needs at least one view")
    return {"kind": "answer", "views": views}, errors
