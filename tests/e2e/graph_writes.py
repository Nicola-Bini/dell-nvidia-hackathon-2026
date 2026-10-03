"""Owner-side graph writes done straight in the database, as cac_owner.

They stand in for the Owner tools API so the Serve side of each loop can be proven on its
own: the same rows the API writes (SCHEMA 8.6), then reindex and publish. The tests in
test_e2e_owner_api.py drive the same loops through je's real API.
"""

from __future__ import annotations

import psycopg
from cac_common.graph import publish, reindex_node
from psycopg.types.json import Jsonb


def add_node(conn: psycopg.Connection, business_id: str, node: dict) -> None:
    """Insert an approved public node and index it. `node`: id, label, name, props, and
    optionally source_type ('owner' or 'agent') and verified."""
    verified = bool(node.get("verified", False))
    conn.execute(
        "INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
        " source_type, verified_by_owner, verified_at)"
        " VALUES (%s, %s, %s, %s, %s, 'public', 'approved', %s, %s,"
        " CASE WHEN %s THEN now() END)",
        (node["id"], business_id, node["label"], node["name"], Jsonb(node["props"]),
         node.get("source_type", "agent"), verified, verified),
    )
    reindex_node(conn, node["id"])


def add_edge(conn: psycopg.Connection, business_id: str, edge: tuple[str, str, str]) -> None:
    src, dst, edge_type = edge
    conn.execute(
        "INSERT INTO kg.edge (business_id, src, dst, type, status, source_type,"
        " verified_by_owner) VALUES (%s, %s, %s, %s, 'approved', 'owner', true)",
        (business_id, src, dst, edge_type),
    )


def add_label(conn: psycopg.Connection, label: str, public_props: list[str]) -> None:
    conn.execute(
        "INSERT INTO kg.label (label, may_be_public, public_props, description, created_by)"
        " VALUES (%s, true, %s, %s, 'agent')",
        (label, public_props, f"{label} (added by the agent)"),
    )


def remove(conn: psycopg.Connection, business_id: str, node_ids: list[str],
           labels: tuple[str, ...] = ()) -> None:
    """Delete test nodes (their edges cascade) and labels, then publish the clean graph."""
    conn.execute("DELETE FROM kg.node WHERE id = ANY(%s)", (node_ids,))
    for label in labels:
        conn.execute("DELETE FROM kg.label WHERE label = %s", (label,))
    publish(conn, business_id)


__all__ = ["add_edge", "add_label", "add_node", "publish", "remove"]
