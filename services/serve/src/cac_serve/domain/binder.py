"""The binder (SCHEMA 8.3, 8.4): a model selection plus code-extracted slots become a Surface.

Pure domain code: no database, no HTTP, no clock (today is a parameter). Every word and
number a visitor sees comes from the graph snapshot or a fixed template. A diet badge is
verified only for an owner-verified edge, and an allergen never produces a list of dishes.
"""

from __future__ import annotations

import uuid
from datetime import date

from cac_serve.domain import templates
from cac_serve.domain.bind_core import BoundView, entry_for, facts
from cac_serve.domain.bind_menu import COMPONENT as MENU_LIST
from cac_serve.domain.bind_menu import bind_menu_list, section_views
from cac_serve.domain.bind_views import BUILDERS, allergen_notice, goal_cta
from cac_serve.domain.graph import Graph, Node
from cac_serve.domain.validate import clean_selection

__all__ = [
    "bind", "busy_surface", "clean_selection", "preset_surface", "steer_shown", "surface_text",
]

ALLERGEN_NOTICE = "AllergenNotice"
GOAL_CTA = "GoalCTA"
_PRESET_COMPONENTS = {
    "booking": "BookingForm", "catering": "CateringQuoteForm", "hours": "HoursCard",
}


def _surface_id() -> str:
    return f"s_{uuid.uuid4().hex[:12]}"


def _meta(graph: Graph, cache: str) -> dict:
    return {"cache": cache, "latency_ms": 0, "graph_version": graph.version, "model": "local"}


def _bootstrap_chips(graph: Graph) -> list[str]:
    business = graph.business()
    chips = business.props.get("chips") if business is not None else None
    return [c for c in chips if isinstance(c, str)] if isinstance(chips, list) else []


def _fixed(graph: Graph, kind: str, words: tuple[str, str], views: list[dict]) -> dict:
    """A fixed surface (gap, off topic): no catalog `say`, no GoalCTA, bootstrap chips."""
    return {
        "surface_id": _surface_id(), "kind": kind, "title": words[0], "say": words[1],
        "views": views, "chips": _bootstrap_chips(graph), "meta": _meta(graph, "miss"),
    }


def _phone_view(business: Node | None) -> list[dict]:
    phone = [f for f in facts(business) if f["name"] == "Phone"] if business else []
    if not phone:
        return []
    data = {"title": templates.GAP_TITLE, "label": business.label, "facts": phone,
            "verified": business.verified is True}
    text = f"{templates.GAP_SAY} Phone: {phone[0]['value']}."
    return [{"id": "v1", "component": "FactCard", "data": data, "actions": [], "text": text}]


def gap_surface(graph: Graph) -> dict:
    """Rule 2: the fixed gap surface with the phone from the Business node."""
    words = (templates.GAP_TITLE, templates.GAP_SAY)
    return _fixed(graph, "gap", words, _phone_view(graph.business()))


def off_topic_surface(graph: Graph) -> dict:
    """Rule 3: the fixed off-topic surface."""
    return _fixed(graph, "off_topic", (templates.OFF_TOPIC_TITLE, templates.OFF_TOPIC_SAY), [])


def _safe_views(views: list) -> list[dict]:
    """Never a list of dishes beside a selected AllergenNotice; one notice per surface."""
    views = [v for v in views if isinstance(v, dict)]
    components = {v.get("component") for v in views}
    if ALLERGEN_NOTICE in components:
        views = [v for v in views if v.get("component") != MENU_LIST]
    seen: set = set()
    unique = []
    for view in views:
        if view.get("component") not in seen:
            seen.add(view.get("component"))
            unique.append(view)
    return unique


def _bind_view(graph: Graph, view: dict, slots: dict, today: date) -> list[BoundView]:
    if entry_for(graph, view) is None:
        return []
    if view.get("component") == MENU_LIST:
        menu = bind_menu_list(graph, view)
        return [menu, allergen_notice(graph)] if menu is not None else []
    builder = BUILDERS.get(view.get("component"))
    bound = builder(graph, view, slots, today) if builder else None
    return [bound] if bound is not None else []


def _first_entry_prop(bound: list[BoundView], key: str):
    entry = bound[0].entry
    return entry.props.get(key) if entry is not None else None


def _assemble(graph: Graph, kind: str, bound: list[BoundView], words: dict | None = None) -> dict:
    """Rules 7 to 9: append the GoalCTA, then fill title, say, chips and view ids."""
    words = words or {}
    first = bound[0]
    title = words.get("title") or templates.rail_title(
        first.data.get("title"), _first_entry_prop(bound, "rail_label"), first.component
    )
    say = words.get("say") or first.say or _first_entry_prop(bound, "say") or ""
    chips = _first_entry_prop(bound, "chips")
    cta = goal_cta(graph, bound)
    views = [
        {"id": f"v{n}", "component": v.component, "data": v.data, "actions": v.actions,
         "text": v.text}
        for n, v in enumerate([*bound, *([cta] if cta else [])], start=1)
    ]
    return {
        "surface_id": _surface_id(), "kind": kind, "title": title, "say": say, "views": views,
        "chips": list(chips) if isinstance(chips, list) else [],
        "meta": _meta(graph, "preset" if kind == "preset" else "miss"),
    }


def bind(graph: Graph, selection: dict, slots: dict, today: date) -> dict:
    """Bind a cleaned selection. Anything that cannot be bound becomes the gap surface."""
    kind = selection.get("kind")
    if kind == "off_topic":
        return off_topic_surface(graph)
    if kind != "answer":
        return gap_surface(graph)
    bound: list[BoundView] = []
    for view in _safe_views(selection.get("views") or []):
        bound += _bind_view(graph, view, slots or {}, today)
    return _assemble(graph, "answer", bound) if bound else gap_surface(graph)


def _menu_preset(graph: Graph, say: str) -> dict:
    lists = section_views(graph)
    bound = [*lists, allergen_notice(graph)] if lists else []
    entry = graph.component(MENU_LIST)
    title = (entry.props.get("rail_label") if entry else None) or "Menu"
    if not bound:
        surface = gap_surface(graph)
        return {**surface, "kind": "preset", "meta": _meta(graph, "preset")}
    return _assemble(graph, "preset", bound, {"title": title[: templates.TITLE_MAX], "say": say})


def preset_surface(graph: Graph, preset: str, today: date) -> dict | None:
    """A fixed surface served with no model call; None for an unknown preset."""
    if preset == "menu":
        return _menu_preset(graph, templates.MENU_SAY)
    component = _PRESET_COMPONENTS.get(preset)
    if component is None:
        return None
    bound = _bind_view(graph, {"component": component}, {}, today)
    if not bound:
        return {**gap_surface(graph), "kind": "preset", "meta": _meta(graph, "preset")}
    return _assemble(graph, "preset", bound)


def busy_surface(graph: Graph, today: date) -> dict:
    """Rule 1 fallback: the menu preset with the "we're busy" note (no part depends on today)."""
    return _menu_preset(graph, templates.BUSY_SAY)


def surface_text(surface: dict) -> str:
    """The views' `text` joined for assistants; the `say` line when no view has text."""
    texts = [v.get("text") for v in surface.get("views") or []]
    joined = "\n".join(t for t in texts if t)
    return joined or surface.get("say") or ""


def steer_shown(surface: dict) -> bool:
    """True when the surface carries a GoalCTA view."""
    return any(v.get("component") == GOAL_CTA for v in surface.get("views") or [])
