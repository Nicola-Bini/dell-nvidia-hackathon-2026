"""GET /v1/bootstrap: what the widget needs before the first intent, read from kg_public."""

from __future__ import annotations

from cac_serve.domain.graph import Graph
from cac_serve.infra import db
from cac_serve.infra.graph_repo import load_graph

_TRAIT_PREFIX = "trait_"


def build_bootstrap(graph: Graph) -> dict | None:
    """The bootstrap payload for a published graph, or None when nothing is published."""
    business = graph.business()
    if graph.version == 0 or business is None:
        return None
    theme = {
        trait.id.removeprefix(_TRAIT_PREFIX): trait.props.get("value")
        for trait in sorted(graph.by_label("BrandTrait"), key=lambda n: n.id)
    }
    nav = [
        {"label": entry["label"], "preset": entry["preset"]}
        for entry in business.props.get("nav") or []
        if isinstance(entry, dict) and "label" in entry and "preset" in entry
    ]
    return {
        "business": {"name": business.name, "tagline": business.props.get("tagline", "")},
        "theme": theme,
        "nav": nav,
        "chips": list(business.props.get("chips") or []),
    }


def get_bootstrap(business_id: str) -> dict | None:
    with db.snapshot() as conn:
        graph = load_graph(conn, business_id)
    return build_bootstrap(graph)
