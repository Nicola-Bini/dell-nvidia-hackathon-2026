"""Graph write helpers shared by the seed and the Owner tools API (OWNERSHIP seam 2).

Neither function commits: the caller owns the transaction.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import tuple_row

from cac_common.embedding import embed
from cac_common.search_text import build_search_text

_SELECT_NODE = """
    SELECT n.name, n.props, l.public_props
    FROM kg.node n
    JOIN kg.label l ON l.label = n.label
    WHERE n.id = %s
"""
_UPDATE_NODE = """
    UPDATE kg.node
    SET search_text = %s, embedding = %s::vector, updated_at = now()
    WHERE id = %s
"""


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def reindex_node(conn: psycopg.Connection, node_id: str) -> None:
    """Rebuild `search_text` and `embedding` for one node. Call after every create or update.

    `search_text` comes from `name` and the label's `public_props` only. `embedding` is NULL
    when no embedder is configured. Raises LookupError when the node does not exist.
    """
    with conn.cursor(row_factory=tuple_row) as cur:
        row = cur.execute(_SELECT_NODE, (node_id,)).fetchone()
        if row is None:
            raise LookupError(f"no kg.node with id {node_id!r}")
        name, props, public_props = row
        text = build_search_text(name, props, public_props)
        vectors = embed([text])
        literal = _vector_literal(vectors[0]) if vectors else None
        cur.execute(_UPDATE_NODE, (text, literal, node_id))


def publish(conn: psycopg.Connection, business_id: str) -> int:
    """Run `kg.publish()` for the business and return the new graph version."""
    with conn.cursor(row_factory=tuple_row) as cur:
        row = cur.execute("SELECT kg.publish(%s)", (business_id,)).fetchone()
    return int(row[0])
