"""db/search.sql: pg_trgm and the full-text fallback indexes, usable by cac_serve."""

import pytest


def test_pg_trgm_is_installed(serve_conn):
    row = serve_conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'").fetchone()
    assert row == (1,)


@pytest.mark.parametrize("schema", ["kg_public", "kg"])
def test_search_text_has_tsvector_and_trigram_gin_indexes(owner_conn, schema):
    rows = owner_conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = 'node'",
        (schema,),
    ).fetchall()
    defs = [r[0].lower() for r in rows]
    assert any("using gin" in d and "to_tsvector('english'" in d for d in defs), defs
    assert any("using gin" in d and "gin_trgm_ops" in d for d in defs), defs


def test_serve_role_can_use_word_similarity(serve_conn):
    row = serve_conn.execute(
        "SELECT word_similarity('guiness', search_text) FROM kg_public.node LIMIT 1"
    ).fetchone()
    assert 0.0 <= row[0] <= 1.0
    assert serve_conn.execute("SELECT similarity('guiness', 'guinness')").fetchone()[0] > 0.5


def test_trigram_search_finds_a_misspelt_item(serve_conn):
    row = serve_conn.execute(
        "SELECT id FROM kg_public.node WHERE label = 'MenuItem'"
        " ORDER BY word_similarity('guiness', search_text) DESC, id LIMIT 1"
    ).fetchone()
    assert row == ("mi_guinness",)


def test_full_text_search_finds_a_diet_by_synonym(serve_conn):
    rows = serve_conn.execute(
        "SELECT id FROM kg_public.node WHERE label = 'Diet'"
        " AND to_tsvector('english', search_text) @@ plainto_tsquery('english', 'celiac')"
    ).fetchall()
    assert rows == [("diet_gluten_free",)]
