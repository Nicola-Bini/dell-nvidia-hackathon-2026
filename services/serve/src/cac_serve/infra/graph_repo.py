"""Loads the published graph as cac_serve. Runs inside the caller's transaction."""

from __future__ import annotations

import psycopg

from cac_serve.domain.graph import Edge, Graph, Node


def load_graph(conn: psycopg.Connection, business_id: str) -> Graph:
    """Snapshot kg_public for one business. Version 0 means nothing is published yet."""
    row = conn.execute(
        "SELECT graph_version FROM kg_public.meta WHERE business_id = %s", (business_id,)
    ).fetchone()
    version = row[0] if row else 0
    nodes = [
        Node(id=r[0], label=r[1], name=r[2], props=r[3], verified=r[4], verified_at=r[5])
        for r in conn.execute(
            "SELECT id, label, name, props, verified_by_owner, verified_at"
            " FROM kg_public.node WHERE business_id = %s ORDER BY id",
            (business_id,),
        )
    ]
    edges = [
        Edge(src=r[0], dst=r[1], type=r[2], props=r[3], verified=r[4])
        for r in conn.execute(
            "SELECT e.src, e.dst, e.type, e.props, e.verified_by_owner"
            " FROM kg_public.edge e JOIN kg_public.node n ON n.id = e.src"
            " WHERE n.business_id = %s ORDER BY e.src, e.type, e.dst",
            (business_id,),
        )
    ]
    return Graph(business_id, version, nodes, edges)
