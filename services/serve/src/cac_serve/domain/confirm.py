"""The fixed confirmation shown after a lead is stored. Template words only."""

from __future__ import annotations

import uuid

from cac_serve.domain.graph import Graph

TITLE = "Request sent"
SAY = "Thanks. {name} has your request and will get back to you to confirm."


def confirmation_surface(graph: Graph) -> dict:
    business = graph.business()
    name = business.name if business is not None else "The team"
    chips = (business.props.get("chips") if business is not None else None) or []
    return {
        "surface_id": f"s_{uuid.uuid4().hex[:12]}", "kind": "answer", "title": TITLE,
        "say": SAY.format(name=name), "views": [], "chips": list(chips),
        "meta": {"cache": "preset", "latency_ms": 0, "graph_version": graph.version,
                 "model": "local"},
    }
