"""Binding for every component except MenuList (SCHEMA 8.3 rules 5 to 9, data shapes 8.4).

Each builder takes the selected view and returns a BoundView, or None when the graph has
nothing to show for it. All text is a graph fact or a fixed template.
"""

from __future__ import annotations

import re
from datetime import date

from cac_serve.domain import hours, templates
from cac_serve.domain.bind_core import (
    BoundView,
    action,
    business_name,
    entry_for,
    facts,
    form_entry,
    service,
)
from cac_serve.domain.bind_menu import menu_items
from cac_serve.domain.graph import Graph, Node

_FIELD_KEYS = ("name", "type", "label", "required", "options")
_PROSE_PROPS = ("details", "description")
_NO_CARD_LABELS = ("UIComponent",)



def _plain_name(name: str) -> str:
    """A form with no title or rail label is titled from its node name: "GiftCardRequest"
    reads "Gift card request"."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name or "").replace("_", " ").split()
    return " ".join(words).capitalize() or "Form"

def _present(slots: dict, keys: tuple[str, ...]) -> dict:
    return {key: slots[key] for key in keys if slots.get(key) is not None}


def bind_answer(graph: Graph, sel: dict, _slots: dict, _today: date) -> BoundView | None:
    node = graph.get(sel.get("faq") or "")
    if node is None or node.label != "FAQ" or not node.props.get("answer"):
        return None
    question = node.props.get("question") or node.name
    answer = node.props["answer"]
    verified_at = node.verified_at.isoformat() if node.verified_at else None
    return BoundView(
        component="Answer",
        data={"question": question, "answer": answer, "verified": node.verified is True,
              "verified_at": verified_at},
        text=f"{question} {answer}",
        entry=entry_for(graph, sel),
    )


def allergen_notice(graph: Graph) -> BoundView:
    """The notice inserted beside any MenuList: no allergen, the fixed sentence."""
    return BoundView(
        component="AllergenNotice",
        data={"allergen": None, "contains": []},
        text=templates.ALLERGEN_NOTICE,
        entry=graph.component("AllergenNotice"),
    )


def _contains(graph: Graph, allergen_id: str) -> list[dict]:
    """Only dishes with an owner-verified CONTAINS_ALLERGEN edge, in menu order."""
    confirmed = {
        e.src for e in graph.in_edges(allergen_id, "CONTAINS_ALLERGEN") if e.verified is True
    }
    listed = [n for n in menu_items(graph) if n.id in confirmed]
    listed_ids = {n.id for n in listed}
    unlisted = sorted(
        (n for n in map(graph.get, confirmed - listed_ids) if n and n.label == "MenuItem"),
        key=lambda n: n.id,
    )
    return [{"id": n.id, "name": n.name} for n in [*listed, *unlisted]]


def bind_allergen(graph: Graph, sel: dict, _slots: dict, _today: date) -> BoundView:
    node = graph.get(sel.get("allergen") or "")
    if node is None or node.label != "Allergen" or not node.name:
        return allergen_notice(graph)
    name = node.name.lower()
    contains = _contains(graph, node.id)
    text = templates.ALLERGEN_WARNING.format(allergen=name)
    if contains:
        names = ", ".join(item["name"] for item in contains)
        text = f"{text} {templates.ALLERGEN_CONTAINS.format(allergen=name, names=names)}"
    return BoundView(
        component="AllergenNotice",
        data={"allergen": name, "contains": contains},
        text=text,
        entry=graph.component("AllergenNotice"),
    )


def bind_hours(graph: Graph, sel: dict, slots: dict, today: date) -> BoundView:
    data = hours.hours_data(graph, hours.slot_date(slots, today))
    return BoundView(
        component="HoursCard",
        data=data,
        text=hours.hours_text(data),
        entry=entry_for(graph, sel),
        say=hours.hours_say(data),
    )


def _booking_text(graph: Graph, prefill: dict, booking_url: str | None) -> str:
    request = f"Request a table at {business_name(graph)}"
    if "party_size" in prefill:
        request += f" for {prefill['party_size']}"
    if "date" in prefill:
        request += f" on {prefill['date']}"
    if "time" in prefill:
        request += f" at {prefill['time']}"
    text = f"{request}. {templates.BOOKING_DISCLAIMER}"
    return f"{text} Online booking: {booking_url}" if booking_url else text


def bind_booking(graph: Graph, sel: dict, slots: dict, _today: date) -> BoundView | None:
    reservations = service(graph, "reservations")
    if reservations is None:
        return None  # the business has not said it takes table requests
    prefill = _present(slots, ("date", "time", "party_size"))
    data: dict = {"prefill": prefill}
    booking_url = reservations.props.get("booking_url") or None
    if booking_url:
        data["booking_url"] = booking_url
    return BoundView(
        component="BookingForm",
        data=data,
        text=_booking_text(graph, prefill, booking_url),
        actions=[action("submit_booking_request", "server")],
        entry=entry_for(graph, sel),
    )


def _catering_text(graph: Graph, catering: Node, prefill: dict) -> str:
    request = "Request a catering quote"
    if "headcount" in prefill:
        request += f" for {prefill['headcount']} guests"
    if "date" in prefill:
        request += f" on {prefill['date']}"
    parts = [f"{business_name(graph)} catering:"]
    parts.append(templates.sentence(templates.fact_value(catering.props.get("details"))))
    parts.append(f"{request}.")
    minimum = templates.fact_value(catering.props.get("min_headcount"))
    if minimum:
        parts.append(f"Minimum headcount: {minimum}.")
    return " ".join(part for part in parts if part)


def bind_catering(graph: Graph, sel: dict, slots: dict, _today: date) -> BoundView | None:
    catering = service(graph, "catering")
    if catering is None:
        return None
    prefill = _present(slots, ("headcount", "date"))
    return BoundView(
        component="CateringQuoteForm",
        data={"prefill": prefill, "min_headcount": catering.props.get("min_headcount")},
        text=_catering_text(graph, catering, prefill),
        actions=[action("submit_catering_quote", "server")],
        entry=entry_for(graph, sel),
    )


def _fact_text(node: Node, rows: list[dict]) -> str:
    """The node's free-text prop when it has one, else every fact spelled out."""
    for key in _PROSE_PROPS:
        prose = templates.fact_value(node.props.get(key))
        if prose:
            return f"{node.name}: {templates.sentence(prose)}"
    spelled = "; ".join(f"{row['name']}: {row['value']}" for row in rows)
    return templates.sentence(f"{node.name}: {spelled}" if spelled else node.name)


def bind_fact_card(graph: Graph, sel: dict, _slots: dict, _today: date) -> BoundView | None:
    node = graph.get(sel.get("node") or "")
    if node is None or node.label in _NO_CARD_LABELS:
        return None
    rows = facts(node)
    return BoundView(
        component="FactCard",
        data={"title": node.name, "label": node.label, "facts": rows,
              "verified": node.verified is True},
        text=_fact_text(node, rows),
        entry=entry_for(graph, sel),
    )


def _shared_facts(items: list[dict]) -> list[dict]:
    """Facts that are identical on every item, stated once in the text."""
    first, rest = items[0]["facts"], items[1:]
    return [row for row in first if all(row in other["facts"] for other in rest)]


def bind_list_card(graph: Graph, sel: dict, _slots: dict, _today: date) -> BoundView | None:
    label = sel.get("label")
    if not isinstance(label, str) or label in _NO_CARD_LABELS:
        return None
    nodes = sorted(graph.by_label(label), key=lambda n: n.id)[: templates.LIST_CAP]
    if not nodes:
        return None
    title = templates.plural_label(label)
    items = [{"id": n.id, "name": n.name, "facts": facts(n)} for n in nodes]
    parts = [f"{title}: {'; '.join(n.name for n in nodes)}."]
    parts += [templates.sentence(f"{r['name']}: {r['value']}") for r in _shared_facts(items)]
    return BoundView(
        component="ListCard",
        data={"title": title, "items": items},
        text=" ".join(parts),
        entry=entry_for(graph, sel),
    )


def _fields(entry: Node) -> list[dict]:
    """The form's fields, copied from the catalog entry key by key."""
    raw = entry.props.get("fields")
    rows = [f for f in raw if isinstance(f, dict)] if isinstance(raw, list) else []
    return [{k: f[k] for k in _FIELD_KEYS if f.get(k) is not None} for f in rows]


def bind_form_card(graph: Graph, sel: dict, _slots: dict, _today: date) -> BoundView | None:
    entry = form_entry(graph, sel.get("form"))
    if entry is None:
        return None
    own_title = entry.props.get("title")
    fields = _fields(entry)
    lead = own_title or f"Send {business_name(graph)} a message"
    labels = ", ".join(str(f.get("label") or f.get("name") or "") for f in fields)
    return BoundView(
        component="FormCard",
        data={
            "form": entry.id,
            "title": own_title or entry.props.get("rail_label") or _plain_name(entry.name),
            "fields": fields,
            "submit_label": entry.props.get("submit_label") or "Send",
        },
        text=templates.sentence(f"{lead}: {labels}" if labels else lead),
        actions=[action("submit_form", "server")],
        entry=entry,
    )


def goal_cta(graph: Graph, bound: list[BoundView]) -> BoundView | None:
    """Rule 7: one CTA for the highest-steer entry, unless a view already carries steer."""
    if any(v.entry is not None and v.entry.props.get("steer") is not None for v in bound):
        return None
    steered = [
        e for e in graph.catalog()
        if isinstance(e.props.get("steer"), int | float)
        and e.props.get("cta_label") and e.props.get("preset")
    ]
    if not steered:
        return None
    best = max(steered, key=lambda e: (e.props["steer"], e.props["preset"]))
    return BoundView(
        component="GoalCTA",
        data={"label": best.props["cta_label"]},
        text="",
        actions=[action(f"open_view:{best.props['preset']}", "client")],
        entry=graph.component("GoalCTA"),
    )


BUILDERS = {
    "Answer": bind_answer,
    "AllergenNotice": bind_allergen,
    "HoursCard": bind_hours,
    "BookingForm": bind_booking,
    "CateringQuoteForm": bind_catering,
    "FactCard": bind_fact_card,
    "ListCard": bind_list_card,
    "FormCard": bind_form_card,
}
