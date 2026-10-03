"""An in-memory snapshot of the published graph (kg_public) for one request.

The graph is small (a few hundred nodes), so each request loads it once inside its
REPEATABLE READ transaction and retrieval, schema building and binding all read the same
snapshot (SCHEMA 8.3 rule 10). Nothing here is cached between requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    name: str
    props: dict[str, Any]
    verified: bool = False
    verified_at: datetime | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    verified: bool = False


class Graph:
    """Read-only view over published nodes and edges."""

    def __init__(self, business_id: str, version: int, nodes: list[Node], edges: list[Edge]):
        self.business_id = business_id
        self.version = version
        self.nodes: dict[str, Node] = {n.id: n for n in nodes}
        self.edges: list[Edge] = list(edges)
        self._out: dict[str, list[Edge]] = {}
        self._in: dict[str, list[Edge]] = {}
        for edge in self.edges:
            self._out.setdefault(edge.src, []).append(edge)
            self._in.setdefault(edge.dst, []).append(edge)

    def get(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def by_label(self, label: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.label == label]

    def out_edges(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        edges = self._out.get(node_id, [])
        return [e for e in edges if edge_type is None or e.type == edge_type]

    def in_edges(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        edges = self._in.get(node_id, [])
        return [e for e in edges if edge_type is None or e.type == edge_type]

    def business(self) -> Node | None:
        return self.nodes.get(self.business_id)

    def catalog(self) -> list[Node]:
        """Approved UIComponent entries (SCHEMA section 7), in id order."""
        return sorted(self.by_label("UIComponent"), key=lambda n: n.id)

    def component(self, name: str) -> Node | None:
        """The base catalog entry for a purpose-built or generic component name."""
        for node in self.catalog():
            if node.props.get("component") == name and not node.props.get("primitive"):
                return node
        return None

    def forms(self) -> list[Node]:
        """Configured FormCard entries (catalog entries with primitive == "FormCard")."""
        return [n for n in self.catalog() if n.props.get("primitive") == "FormCard"]

    def extended(self, nodes: list[Node] = (), edges: list[Edge] = ()) -> Graph:
        """A copy with extra nodes and edges (later ones win). Used by tests."""
        merged = {**self.nodes, **{n.id: n for n in nodes}}
        return Graph(self.business_id, self.version, list(merged.values()),
                     [*self.edges, *edges])
