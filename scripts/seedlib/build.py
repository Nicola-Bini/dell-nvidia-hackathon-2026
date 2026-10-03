"""Turn seed.yaml and demo-overlay.yaml into graph nodes and edges. Pure: no database.

Shape of the input: docs/SCHEMA.md section 9 and demo/kenmore/README.md.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from seedlib.registry import UI_KEYS

DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = dict(
    zip(
        DAY_ORDER,
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        strict=True,
    )
)
NOT_PROPS = {"id", "name", "source_url"}


@dataclass
class Node:
    id: str
    label: str
    name: str
    props: dict[str, Any]
    visibility: str = "public"
    source_url: str | None = None
    verified: bool = False


@dataclass
class Edge:
    src: str
    dst: str
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    verified: bool = False


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], Edge] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"seed defines node {node.id} twice")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """One edge per (src, dst, type). A verified edge wins over an unverified one."""
        for end in (edge.src, edge.dst):
            if end not in self.nodes:
                raise ValueError(f"{edge.type} edge refers to unknown node {end}")
        key = (edge.src, edge.dst, edge.type)
        known = self.edges.get(key)
        if known is None:
            self.edges[key] = edge
            return
        known.props.update(edge.props)
        known.verified = known.verified or edge.verified


def snake_case(component: str) -> str:
    """BookingForm -> booking_form, GoalCTA -> goal_cta."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", component).lower()


def hours_name(days: list[str]) -> str:
    """A readable name for an HoursSpec: one day, a run of days, or a list."""
    names = [DAY_NAMES[day] for day in days]
    indexes = [DAY_ORDER.index(day) for day in days]
    is_run = indexes == list(range(indexes[0], indexes[0] + len(indexes)))
    if len(names) == 1:
        label = names[0]
    elif is_run:
        label = f"{names[0]} to {names[-1]}"
    else:
        label = ", ".join(names)
    return f"Opening hours: {label}"


def _props(entry: dict[str, Any], skip: frozenset[str] = frozenset()) -> dict[str, Any]:
    """The entry without its node columns. YAML dates become YYYY-MM-DD strings."""
    props = {}
    for key, value in entry.items():
        if key in NOT_PROPS or key in skip:
            continue
        props[key] = value.isoformat() if isinstance(value, dt.date) else value
    return props


def _add_business(graph: Graph, seed: dict, overlay: dict) -> str:
    business = seed["business"]
    props = _props(business)
    bootstrap = overlay.get("bootstrap") or {}
    props["nav"] = bootstrap.get("nav") or []
    props["chips"] = bootstrap.get("chips") or []
    node = Node(business["id"], "Business", business["name"], props)
    node.source_url = business.get("source_url")
    graph.add_node(node)
    location = seed["location"]
    graph.add_node(
        Node(location["id"], "Location", location["name"], _props(location),
             source_url=location.get("source_url"))
    )  # fmt: skip
    graph.add_edge(Edge(business["id"], location["id"], "HAS_LOCATION"))
    return business["id"]


def _add_hours(graph: Graph, biz: str, sources: list[dict]) -> None:
    for source in sources:
        for entry in source.get("hours") or []:
            graph.add_node(Node(entry["id"], "HoursSpec", hours_name(entry["days"]),
                                _props(entry)))  # fmt: skip
            graph.add_edge(Edge(biz, entry["id"], "HAS_HOURS"))
        for entry in source.get("special_hours") or []:
            graph.add_node(Node(entry["id"], "SpecialHours", entry["note"], _props(entry)))
            graph.add_edge(Edge(biz, entry["id"], "HAS_HOURS"))


def _menu_item(entry: dict) -> Node:
    props = {"currency": "USD", "available": True, **_props(entry)}
    return Node(entry["id"], "MenuItem", entry["name"], props,
                source_url=entry.get("source_url"))  # fmt: skip


def _add_menu(graph: Graph, biz: str, seed: dict) -> None:
    sections = seed.get("sections") or []
    for position, section in enumerate(sections, start=1):
        graph.add_node(Node(section["id"], "MenuSection", section["name"],
                            {"position": position}))  # fmt: skip
        graph.add_edge(Edge(biz, section["id"], "HAS_SECTION"))
        for entry in section["items"]:
            if "id" in entry:
                graph.add_node(_menu_item(entry))
    # Second pass: a `ref` may point at an item defined in a later section.
    for section in sections:
        for position, entry in enumerate(section["items"], start=1):
            item_id = entry.get("id") or entry["ref"]
            graph.add_edge(Edge(section["id"], item_id, "HAS_ITEM", {"position": position}))


def _add_reference(graph: Graph, biz: str, sources: list[dict]) -> None:
    for source in sources:
        for key, label in (("diets", "Diet"), ("allergens", "Allergen")):
            for entry in source.get(key) or []:
                graph.add_node(Node(entry["id"], label, entry["name"], _props(entry)))
        for entry in source.get("services") or []:
            name = entry.get("name") or entry["kind"].replace("_", " ").capitalize()
            graph.add_node(Node(entry["id"], "Service", name, _props(entry),
                                source_url=entry.get("source_url")))  # fmt: skip
            graph.add_edge(Edge(biz, entry["id"], "OFFERS"))
        for entry in source.get("brand") or []:
            name = entry["id"].removeprefix("trait_").replace("_", " ")
            graph.add_node(Node(entry["id"], "BrandTrait", name, _props(entry)))


def _add_faqs(graph: Graph, sources: list[dict]) -> None:
    for source in sources:
        for entry in source.get("faqs") or []:
            props = {"question": entry["question"], "answer": entry["answer"]}
            graph.add_node(Node(entry["id"], "FAQ", entry["question"], props,
                                source_url=entry.get("source_url")))  # fmt: skip
            for target in entry.get("answers") or []:
                graph.add_edge(Edge(entry["id"], target, "ANSWERS"))


def _add_components(graph: Graph, overlay: dict) -> None:
    for entry in overlay.get("ui_components") or []:
        unknown = set(entry) - set(UI_KEYS) - {"id"}
        if unknown:
            raise ValueError(f"{entry['id']} has keys outside the catalog: {sorted(unknown)}")
        props = {key: entry.get(key) for key in UI_KEYS}
        name = entry.get("rail_label") or entry["component"]
        graph.add_node(Node(entry["id"], "UIComponent", name, props))


def _add_diet_edges(graph: Graph, seed: dict, overlay: dict) -> None:
    for source, key, verified in ((seed, "unverified_diets", False),
                                  (overlay, "verified_diets", True)):  # fmt: skip
        for diet_id, item_ids in (source.get(key) or {}).items():
            for item_id in item_ids:
                graph.add_edge(Edge(item_id, diet_id, "SUITABLE_FOR", verified=verified))


def _add_private(graph: Graph, overlay: dict) -> None:
    """Goals with their ADVANCES edges, and the canary Customer. None of it is published."""
    for goal in overlay.get("goals") or []:
        props = {"statement": goal["statement"], "priority": goal["priority"]}
        graph.add_node(Node(goal["id"], "Goal", goal["id"].removeprefix("goal_").capitalize(),
                            props, visibility="private", verified=True))  # fmt: skip
        for component in goal.get("advanced_by") or []:
            src = f"ui_{snake_case(component)}"
            graph.add_edge(Edge(src, goal["id"], "ADVANCES", verified=True))
    for customer in (overlay.get("private") or {}).get("customers") or []:
        props = {key: value for key, value in customer.items() if key != "id"}
        graph.add_node(Node(customer["id"], "Customer", customer["name"], props,
                            visibility="private"))  # fmt: skip


def build_graph(seed: dict, overlay: dict) -> Graph:
    """Apply seed.yaml, then the overlay. Raises ValueError on a dangling reference."""
    graph = Graph()
    sources = [seed, overlay]
    biz = _add_business(graph, seed, overlay)
    _add_hours(graph, biz, sources)
    _add_menu(graph, biz, seed)
    _add_reference(graph, biz, sources)
    _add_faqs(graph, sources)
    _add_components(graph, overlay)
    _add_diet_edges(graph, seed, overlay)
    _add_private(graph, overlay)
    return graph
