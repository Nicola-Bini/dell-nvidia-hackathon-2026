"""Raw SQL against `kg` for the change engine. No business rules here."""

import psycopg
from psycopg.types.json import Jsonb

from app.domain.tiers import NodeState, is_locked_label


def get_label(conn: psycopg.Connection, label: str) -> dict | None:
    return conn.execute("SELECT * FROM kg.label WHERE label = %s", (label,)).fetchone()


def get_edge_type(conn: psycopg.Connection, edge_type: str) -> dict | None:
    return conn.execute("SELECT * FROM kg.edge_type WHERE type = %s", (edge_type,)).fetchone()


def get_node(conn: psycopg.Connection, node_id: str) -> dict | None:
    return conn.execute("SELECT * FROM kg.node WHERE id = %s", (node_id,)).fetchone()


def get_edge(conn: psycopg.Connection, src: str, dst: str, edge_type: str) -> dict | None:
    return conn.execute("SELECT * FROM kg.edge WHERE src = %s AND dst = %s AND type = %s",
                        (src, dst, edge_type)).fetchone()


def node_state(conn: psycopg.Connection, node: dict) -> NodeState:
    label = get_label(conn, node["label"]) or {"may_be_public": False, "locked": True}
    return NodeState(label=node["label"], label_public=label["may_be_public"],
                     visibility=node["visibility"],
                     locked=bool(label["locked"]) or is_locked_label(node["label"]))


def insert_label(conn, name: str, after: dict, status: str) -> None:
    conn.execute(
        "INSERT INTO kg.label (label, may_be_public, public_props, description, locked, status,"
        " created_by) VALUES (%s, %s, %s, %s, false, %s, 'agent')",
        (name, bool(after.get("may_be_public")), list(after.get("public_props") or []),
         str(after.get("description") or name)[:300], status))


def insert_edge_type(conn, name: str, after: dict, status: str) -> None:
    conn.execute(
        "INSERT INTO kg.edge_type (type, public_props, description, status, created_by)"
        " VALUES (%s, %s, %s, %s, 'agent')",
        (name, list(after.get("public_props") or []),
         str(after.get("description") or name)[:300], status))


def insert_node(conn, biz: str, node_id: str, node: dict, status: str) -> None:
    conn.execute(
        "INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
        " source_type, extracted_by, verified_by_owner) VALUES"
        " (%s, %s, %s, %s, %s, %s, %s, 'agent', 'agent', false)",
        (node_id, biz, node["label"], node["name"], Jsonb(node["props"]),
         node["visibility"], status))


def update_node(conn, node_id: str, values: dict) -> None:
    """Set name, props, visibility and status from `values` (all four keys)."""
    conn.execute(
        "UPDATE kg.node SET name = %s, props = %s, visibility = %s, status = %s,"
        " updated_at = now() WHERE id = %s",
        (values["name"], Jsonb(values["props"]), values["visibility"], values["status"], node_id))


def set_node_status(conn, node_id: str, status: str) -> None:
    conn.execute("UPDATE kg.node SET status = %s, updated_at = now() WHERE id = %s",
                 (status, node_id))


def upsert_edge(conn, biz: str, key: tuple[str, str, str], props: dict, status: str) -> None:
    src, dst, edge_type = key
    conn.execute(
        "INSERT INTO kg.edge (business_id, src, dst, type, props, status, source_type,"
        " verified_by_owner) VALUES (%s, %s, %s, %s, %s, %s, 'agent', false)"
        " ON CONFLICT (src, dst, type) DO UPDATE SET status = EXCLUDED.status,"
        " props = EXCLUDED.props, source_type = 'agent', verified_by_owner = false,"
        " verified_at = NULL", (biz, src, dst, edge_type, Jsonb(props), status))


def set_edge_status(conn, key: tuple[str, str, str], status: str) -> None:
    conn.execute("UPDATE kg.edge SET status = %s WHERE src = %s AND dst = %s AND type = %s",
                 (status, *key))


def set_label_status(conn, label: str, status: str) -> None:
    conn.execute("UPDATE kg.label SET status = %s WHERE label = %s", (status, label))


def set_edge_type_status(conn, edge_type: str, status: str) -> None:
    conn.execute("UPDATE kg.edge_type SET status = %s WHERE type = %s", (status, edge_type))


def set_public_props(conn, label: str, props: list[str]) -> None:
    conn.execute("UPDATE kg.label SET public_props = %s WHERE label = %s", (props, label))
