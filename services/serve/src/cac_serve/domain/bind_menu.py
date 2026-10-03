"""MenuList binding (SCHEMA 8.3 rules 4 and 5): the list is built in code, never by the model.

A diet badge is `verified: true` only for an owner-verified SUITABLE_FOR edge. A diet list
holds only items that carry an edge to that diet, owner-verified first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cac_serve.domain import templates
from cac_serve.domain.bind_core import BoundView, action
from cac_serve.domain.graph import Graph, Node

COMPONENT = "MenuList"
DIET_ORDER = ("diet_vegetarian", "diet_vegan", "diet_gluten_free")
_LAST = 10**9
_CONFIRMED = "confirmed by the restaurant"
_UNVERIFIED = "not verified, ask staff"


@dataclass
class _Listing:
    title: str
    items: list[Node]
    verified: int | None = None  # diet lists: how many leading items are owner-verified
    named: bool = False


def _position(props: dict) -> int:
    value = props.get("position")
    return value if isinstance(value, int) and not isinstance(value, bool) else _LAST


def sections(graph: Graph) -> list[Node]:
    """MenuSection nodes in site order."""
    return sorted(graph.by_label("MenuSection"), key=lambda n: (_position(n.props), n.id))


def section_items(graph: Graph, section_id: str) -> list[Node]:
    """A section's items in HAS_ITEM position order."""
    edges = sorted(
        graph.out_edges(section_id, "HAS_ITEM"), key=lambda e: (_position(e.props), e.dst)
    )
    nodes = (graph.get(e.dst) for e in edges)
    return _unique([n for n in nodes if n is not None and n.label == "MenuItem"])


def menu_items(graph: Graph) -> list[Node]:
    """Every listed item once, in menu order (section position, then item position)."""
    return _unique([item for sec in sections(graph) for item in section_items(graph, sec.id)])


def _unique(nodes: list[Node]) -> list[Node]:
    seen: dict[str, Node] = {}
    for node in nodes:
        seen.setdefault(node.id, node)
    return list(seen.values())


def _diet_rank(diet_id: str) -> tuple[int, str]:
    rank = DIET_ORDER.index(diet_id) if diet_id in DIET_ORDER else len(DIET_ORDER)
    return rank, diet_id


def badges(graph: Graph, item_id: str) -> list[dict]:
    """Every diet tag on the item; verified only when the edge is owner-verified."""
    tags: dict[str, bool] = {}
    for edge in graph.out_edges(item_id, "SUITABLE_FOR"):
        diet = graph.get(edge.dst)
        if diet is not None and diet.label == "Diet":
            tags[diet.id] = tags.get(diet.id, False) or edge.verified is True
    return [
        {"diet": graph.nodes[diet_id].name, "verified": tags[diet_id]}
        for diet_id in sorted(tags, key=_diet_rank)
    ]


def item_data(graph: Graph, node: Node) -> dict:
    description = node.props.get("description")
    return {
        "id": node.id,
        "name": node.name,
        "price": templates.price(node.props.get("price_cents")),
        "description": description if isinstance(description, str) else "",
        "badges": badges(graph, node.id),
    }


def _typed(graph: Graph, node_id: Any, label: str) -> Node | None:
    node = graph.get(node_id) if isinstance(node_id, str) else None
    return node if node is not None and node.label == label else None


def _pool(graph: Graph, sel: dict, section: Node | None) -> tuple[list[Node], bool]:
    """The items before the diet filter, and whether the visitor named them."""
    named = [_typed(graph, item_id, "MenuItem") for item_id in sel.get("items") or []]
    named = _unique([n for n in named if n is not None])
    if not named:
        return (section_items(graph, section.id) if section else menu_items(graph)), False
    if section is not None:
        in_section = {n.id for n in section_items(graph, section.id)}
        named = [n for n in named if n.id in in_section]
    return named, True


def _diet_tags(graph: Graph, diet_id: str) -> dict[str, bool]:
    """Item id -> owner-verified, for every item with a SUITABLE_FOR edge to the diet."""
    tags: dict[str, bool] = {}
    for edge in graph.in_edges(diet_id, "SUITABLE_FOR"):
        tags[edge.src] = tags.get(edge.src, False) or edge.verified is True
    return tags


def _unknown_filter(graph: Graph, sel: dict) -> bool:
    """True when the selection names a diet or section that is not in the graph."""
    filters = (("diet", "Diet"), ("section", "MenuSection"))
    return any(sel.get(k) and _typed(graph, sel.get(k), label) is None for k, label in filters)


def _listing(graph: Graph, sel: dict, rail_label: str) -> _Listing | None:
    if _unknown_filter(graph, sel):
        return None  # an unknown filter never widens the list
    diet = _typed(graph, sel.get("diet"), "Diet")
    section = _typed(graph, sel.get("section"), "MenuSection")
    pool, named = _pool(graph, sel, section)
    if diet is None:
        return _Listing(section.name if section else rail_label, pool, named=named)
    tags = _diet_tags(graph, diet.id)
    verified = [n for n in pool if tags.get(n.id) is True]
    unverified = [n for n in pool if tags.get(n.id) is False]
    return _Listing(diet.name, verified + unverified, len(verified), named)


def _line(item: dict) -> str:
    return f"{item['name']}, {item['price']}" if item["price"] else item["name"]


def _named_line(item: dict) -> str:
    notes = "; ".join(
        f"{b['diet']}: {_CONFIRMED if b['verified'] else _UNVERIFIED}" for b in item["badges"]
    )
    head = templates.sentence(f"{_line(item)} ({notes})" if notes else _line(item))
    return f"{head} {templates.sentence(item['description'])}".strip()


def _diet_text(title: str, items: list[dict], verified: int) -> str:
    confirmed = "; ".join(_line(i) for i in items[:verified])
    unverified = "; ".join(_line(i) for i in items[verified:])
    if not confirmed:
        return f"{title} ({_UNVERIFIED}): {unverified}."
    text = f"{title} ({_CONFIRMED}): {confirmed}."
    return f"{text} Not verified, ask staff: {unverified}." if unverified else text


def _text(listing: _Listing, items: list[dict], extra: int) -> str:
    if listing.verified is not None:
        text = _diet_text(listing.title, items, min(listing.verified, len(items)))
    elif listing.named:
        text = f"{listing.title}: {' '.join(_named_line(i) for i in items)}"
    else:
        text = f"{listing.title}: {'; '.join(_line(i) for i in items)}."
    return f"{text} {extra} more on the full menu." if extra > 0 else text


def _view(graph: Graph, listing: _Listing, cap: int | None, order: bool) -> BoundView:
    shown = listing.items if cap is None else listing.items[:cap]
    extra = len(listing.items) - len(shown)
    items = [item_data(graph, node) for node in shown]
    more = {"label": templates.MORE_LABEL, "preset": templates.MORE_PRESET} if extra else None
    return BoundView(
        component=COMPONENT,
        data={"title": listing.title, "items": items, "more": more},
        text=_text(listing, items, extra),
        actions=[action("add_to_cart", "client")] if order else [],
        entry=graph.component(COMPONENT),
    )


def bind_menu_list(graph: Graph, sel: dict) -> BoundView | None:
    """A selected MenuList, capped at 12; None when the filters leave nothing to show."""
    entry = graph.component(COMPONENT)
    rail_label = (entry.props.get("rail_label") if entry else None) or "Menu"
    listing = _listing(graph, sel, rail_label)
    if listing is None or not listing.items:
        return None
    return _view(graph, listing, templates.LIST_CAP, sel.get("order") is True)


def section_views(graph: Graph) -> list[BoundView]:
    """The menu preset: one uncapped MenuList per section that has items."""
    views = []
    for section in sections(graph):
        items = section_items(graph, section.id)
        if items:
            views.append(_view(graph, _Listing(section.name, items), None, False))
    return views
