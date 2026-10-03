"""reindex_node and publish against the real database, as cac_owner. Nothing is committed."""

import pytest
from cac_common import graph

NODE_ID = "mi_test_reindex_wp1"
INSERT = """
    INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,
                         source_type, updated_at)
    VALUES (%s, %s, 'MenuItem', 'Test  Stout',
            '{"description": "Dark and roasty", "supplier": "Acme Kegs", "price_cents": 900}',
            'public', 'approved', 'seed', '2000-01-01')
"""
SELECT = "SELECT search_text, embedding::text, updated_at > '2000-01-01' FROM kg.node WHERE id = %s"


def test_reindex_builds_search_text_from_public_props_only(owner_conn, business_id, monkeypatch):
    monkeypatch.setattr(graph, "embed", lambda texts: None)
    owner_conn.execute(INSERT, (NODE_ID, business_id))
    graph.reindex_node(owner_conn, NODE_ID)
    text, embedding, bumped = owner_conn.execute(SELECT, (NODE_ID,)).fetchone()
    assert text == "Test Stout Dark and roasty"
    assert embedding is None
    assert bumped


def test_reindex_stores_the_embedding_when_an_embedder_answers(
    owner_conn, business_id, monkeypatch
):
    seen = []

    def fake_embed(texts):
        seen.extend(texts)
        return [[0.5] + [0.0] * 1023]

    monkeypatch.setattr(graph, "embed", fake_embed)
    owner_conn.execute(INSERT, (NODE_ID, business_id))
    graph.reindex_node(owner_conn, NODE_ID)
    _, embedding, _ = owner_conn.execute(SELECT, (NODE_ID,)).fetchone()
    assert seen == ["Test Stout Dark and roasty"]
    assert embedding.startswith("[0.5,0,")


def test_reindex_does_not_commit(owner_conn, business_id, settings, monkeypatch):
    import psycopg

    monkeypatch.setattr(graph, "embed", lambda texts: None)
    owner_conn.execute(INSERT, (NODE_ID, business_id))
    graph.reindex_node(owner_conn, NODE_ID)
    with psycopg.connect(settings.owner_database_url) as other:
        assert other.execute("SELECT 1 FROM kg.node WHERE id = %s", (NODE_ID,)).fetchone() is None


def test_reindex_unknown_node_raises(owner_conn):
    with pytest.raises(LookupError):
        graph.reindex_node(owner_conn, "mi_does_not_exist")


def test_publish_returns_the_next_version_and_does_not_commit(owner_conn, business_id):
    before = owner_conn.execute(
        "SELECT graph_version FROM kg_public.meta WHERE business_id = %s", (business_id,)
    ).fetchone()[0]
    assert graph.publish(owner_conn, business_id) == before + 1
    owner_conn.rollback()
    after = owner_conn.execute(
        "SELECT graph_version FROM kg_public.meta WHERE business_id = %s", (business_id,)
    ).fetchone()[0]
    assert after == before
