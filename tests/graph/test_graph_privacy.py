"""Privacy invariants of the publish boundary (PRD section 10), on the seeded graph."""

import psycopg
import pytest
from cac_common import graph

CANARY = "Zephyrine Quillfeather"
ITEM = "mi_guinness"
GOAL_STATEMENTS = ("Fill tables on weeknights", "Sign up catering clients")


def _public_props(settings, node_id: str) -> dict:
    with psycopg.connect(settings.serve_database_url) as conn:
        sql = "SELECT props FROM kg_public.node WHERE id = %s"
        return conn.execute(sql, (node_id,)).fetchone()[0]


def test_private_prop_on_a_public_node_is_not_published(owner_conn, settings, business_id):
    add = "UPDATE kg.node SET props = props || '{\"supplier\": \"Acme Kegs\"}' WHERE id = %s"
    drop = "UPDATE kg.node SET props = props - 'supplier' WHERE id = %s"
    try:
        owner_conn.execute(add, (ITEM,))
        graph.publish(owner_conn, business_id)
        owner_conn.commit()
        assert "supplier" not in _public_props(settings, ITEM)
        assert "price_cents" in _public_props(settings, ITEM)
    finally:
        owner_conn.rollback()
        owner_conn.execute(drop, (ITEM,))
        graph.publish(owner_conn, business_id)
        owner_conn.commit()
    kept = owner_conn.execute("SELECT props ? 'supplier' FROM kg.node WHERE id = %s", (ITEM,))
    assert kept.fetchone()[0] is False


def test_unlisted_seed_props_stay_in_kg_only(owner_conn, serve_conn, business_id):
    burger = "SELECT props FROM {} WHERE id = 'mi_the_k_burger'"
    private = owner_conn.execute(burger.format("kg.node")).fetchone()[0]
    public = serve_conn.execute(burger.format("kg_public.node")).fetchone()[0]
    assert private["cooked_to_order"] is True
    assert "cooked_to_order" not in public
    business = "SELECT props FROM {} WHERE id = %s"
    private = owner_conn.execute(business.format("kg.node"), (business_id,)).fetchone()[0]
    public = serve_conn.execute(business.format("kg_public.node"), (business_id,)).fetchone()[0]
    assert private["logo_url"].startswith("https://")
    assert "logo_url" not in public
    for table in ("kg_public.node", "kg_public.edge"):
        leaked = serve_conn.execute(
            f"SELECT count(*) FROM {table}"
            " WHERE props::text ~ '(supplier|cooked_to_order|logo_url)'"
        ).fetchone()[0]
        assert leaked == 0


def test_canary_customer_exists_privately(owner_conn):
    row = owner_conn.execute(
        "SELECT label, visibility, name FROM kg.node WHERE id = 'cust_canary'"
    ).fetchone()
    assert row == ("Customer", "private", CANARY)


@pytest.mark.parametrize("needle", [CANARY, "Quillfeather", "canary@example.invalid"])
def test_canary_is_nowhere_in_kg_public(serve_conn, needle):
    pattern = f"%{needle}%"
    nodes = serve_conn.execute(
        "SELECT count(*) FROM kg_public.node WHERE id = 'cust_canary' OR name ILIKE %(p)s"
        " OR props::text ILIKE %(p)s OR search_text ILIKE %(p)s",
        {"p": pattern},
    ).fetchone()[0]
    edges = serve_conn.execute(
        "SELECT count(*) FROM kg_public.edge WHERE props::text ILIKE %(p)s"
        " OR src = 'cust_canary' OR dst = 'cust_canary'",
        {"p": pattern},
    ).fetchone()[0]
    assert (nodes, edges) == (0, 0)


@pytest.mark.parametrize("statement", GOAL_STATEMENTS)
def test_goal_statements_are_nowhere_in_kg_public(serve_conn, statement):
    pattern = f"%{statement}%"
    nodes = serve_conn.execute(
        "SELECT count(*) FROM kg_public.node WHERE name ILIKE %(p)s"
        " OR props::text ILIKE %(p)s OR search_text ILIKE %(p)s OR id LIKE 'goal\\_%%'",
        {"p": pattern},
    ).fetchone()[0]
    edges = serve_conn.execute(
        "SELECT count(*) FROM kg_public.edge WHERE props::text ILIKE %(p)s"
        " OR dst LIKE 'goal\\_%%'",
        {"p": pattern},
    ).fetchone()[0]
    assert (nodes, edges) == (0, 0)


@pytest.mark.parametrize("table", ["kg.node", "kg.edge", "kg.label", "ops.lead", "ops.intent_log"])
def test_serve_role_is_denied(serve_conn, table):
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
        serve_conn.execute(f"SELECT * FROM {table} LIMIT 1")


def test_serve_role_cannot_publish_or_write_public(serve_conn, business_id):
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
        serve_conn.execute("SELECT kg.publish(%s)", (business_id,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
        serve_conn.execute("UPDATE kg_public.node SET name = name")
