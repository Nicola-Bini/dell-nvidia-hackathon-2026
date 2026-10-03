"""Database writes for the seed: idempotent upserts as cac_owner. Nothing here commits."""

from __future__ import annotations

import time

import psycopg
from cac_common.graph import publish, reindex_node
from cac_common.settings import get_settings
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from seedlib.build import Graph
from seedlib.registry import EDGE_TYPES, LABELS

# A re-run keeps props the seed did not write (for example one the agent added later).
_KEEP_EXTRA = """
    EXCLUDED.public_props || ARRAY(
        SELECT p FROM unnest({table}.public_props) AS p
        WHERE p <> ALL (EXCLUDED.public_props))
"""
_UPSERT_LABEL = f"""
    INSERT INTO kg.label (label, may_be_public, public_props, description, locked, created_by)
    VALUES (%s, %s, %s, %s, %s, 'seed')
    ON CONFLICT (label) DO UPDATE SET
        may_be_public = EXCLUDED.may_be_public,
        public_props = {_KEEP_EXTRA.format(table="kg.label")},
        description = EXCLUDED.description,
        locked = EXCLUDED.locked
"""
_UPSERT_EDGE_TYPE = f"""
    INSERT INTO kg.edge_type (type, public_props, description, created_by)
    VALUES (%s, %s, %s, 'seed')
    ON CONFLICT (type) DO UPDATE SET
        public_props = {_KEEP_EXTRA.format(table="kg.edge_type")},
        description = EXCLUDED.description
"""
_UPSERT_NODE = """
    INSERT INTO kg.node (id, business_id, label, name, props, visibility, status, source_type,
                         source_url, extracted_by, verified_by_owner, verified_at)
    VALUES (%(id)s, %(business_id)s, %(label)s, %(name)s, %(props)s, %(visibility)s,
            'approved', 'seed', %(source_url)s, 'seed', %(verified)s,
            CASE WHEN %(verified)s THEN now() END)
    ON CONFLICT (id) DO UPDATE SET
        business_id = EXCLUDED.business_id,
        label = EXCLUDED.label,
        name = EXCLUDED.name,
        props = kg.node.props || EXCLUDED.props,
        visibility = EXCLUDED.visibility,
        status = EXCLUDED.status,
        source_type = EXCLUDED.source_type,
        source_url = EXCLUDED.source_url,
        verified_by_owner = kg.node.verified_by_owner OR EXCLUDED.verified_by_owner,
        verified_at = COALESCE(kg.node.verified_at, EXCLUDED.verified_at)
"""
_UPSERT_EDGE = """
    INSERT INTO kg.edge (business_id, src, dst, type, props, status, source_type,
                         verified_by_owner, verified_at)
    VALUES (%(business_id)s, %(src)s, %(dst)s, %(type)s, %(props)s, 'approved', 'seed',
            %(verified)s, CASE WHEN %(verified)s THEN now() END)
    ON CONFLICT (src, dst, type) DO UPDATE SET
        business_id = EXCLUDED.business_id,
        props = kg.edge.props || EXCLUDED.props,
        status = EXCLUDED.status,
        source_type = EXCLUDED.source_type,
        verified_by_owner = kg.edge.verified_by_owner OR EXCLUDED.verified_by_owner,
        verified_at = COALESCE(kg.edge.verified_at, EXCLUDED.verified_at)
"""
_COUNTS = "SELECT label, count(*) FROM kg.node WHERE business_id = %s GROUP BY label ORDER BY 1"


def connect(url: str, wait_seconds: float = 60.0) -> psycopg.Connection:
    """Connect as cac_owner, waiting for a database that is still starting.

    Right after `make db-reset` the container reports healthy while its init scripts are
    still running, so the first attempts can be refused.
    """
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return psycopg.connect(url)
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1.0)


def upsert_registries(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            _UPSERT_LABEL,
            [(r.label, r.may_be_public, r.public_props, r.description, r.locked) for r in LABELS],
        )
        cur.executemany(
            _UPSERT_EDGE_TYPE, [(r.type, r.public_props, r.description) for r in EDGE_TYPES]
        )


def upsert_graph(conn: psycopg.Connection, graph: Graph, business_id: str) -> None:
    nodes = [
        {"id": n.id, "business_id": business_id, "label": n.label, "name": n.name,
         "props": Jsonb(n.props), "visibility": n.visibility, "source_url": n.source_url,
         "verified": n.verified}
        for n in graph.nodes.values()
    ]  # fmt: skip
    edges = [
        {"business_id": business_id, "src": e.src, "dst": e.dst, "type": e.type,
         "props": Jsonb(e.props), "verified": e.verified}
        for e in graph.edges.values()
    ]  # fmt: skip
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_NODE, nodes)
        cur.executemany(_UPSERT_EDGE, edges)


def label_counts(conn: psycopg.Connection, business_id: str) -> dict[str, int]:
    with conn.cursor(row_factory=tuple_row) as cur:
        return dict(cur.execute(_COUNTS, (business_id,)).fetchall())


def seed_database(graph: Graph) -> tuple[str, int, dict[str, int]]:
    """Write the graph, reindex every seeded node, publish and commit.

    Returns (business id, new graph version, node count per label).
    """
    settings = get_settings()
    business_id = settings.business_id
    with connect(settings.owner_database_url) as conn:
        upsert_registries(conn)
        upsert_graph(conn, graph, business_id)
        for node_id in graph.nodes:
            reindex_node(conn, node_id)
        version = publish(conn, business_id)
        counts = label_counts(conn, business_id)
        conn.commit()
    return business_id, version, counts
