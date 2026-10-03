"""Integration: the same proofs on Blake's real seed and registry (scripts/seed.py), not on
this lane's small fixture graph. Skipped when the seed loader is not in the checkout."""

import pathlib
import sys

import psycopg
import pytest
from cac_common.settings import get_settings

from app.demo import seed_traffic
from tests.conftest import AGENT, OWNER
from tests.test_change_engine import FORM, post, scalar

SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "scripts"
pytestmark = pytest.mark.skipif(not (SCRIPTS / "seedlib").is_dir(), reason="no seed loader")


@pytest.fixture()
def real(pg, monkeypatch, make_client):
    """A database holding the real Kenmore seed, published."""
    from tests.conftest import TRUNCATE
    with psycopg.connect(pg["admin"], autocommit=True) as admin:
        admin.execute(TRUNCATE)
    monkeypatch.setenv("OWNER_DATABASE_URL", pg["owner"])
    monkeypatch.setenv("EMBED_BASE_URL", "")
    get_settings.cache_clear()
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import yaml
    from seedlib import ROOT
    from seedlib.build import build_graph
    from seedlib.db import seed_database
    demo = ROOT / "demo" / "kenmore"
    load = lambda n: yaml.safe_load((demo / n).read_text(encoding="utf-8"))  # noqa: E731
    seed_database(build_graph(load("seed.yaml"), load("demo-overlay.yaml")))
    yield make_client()
    get_settings.cache_clear()
    sys.modules.pop("seedlib", None)


@pytest.fixture()
def conn(pg, real):
    with psycopg.connect(pg["owner"], row_factory=psycopg.rows.dict_row) as c:
        yield c


def decide(client, change_id, verb):
    return client.post(f"/owner/changes/{change_id}/{verb}", headers=OWNER)


def test_agent_never_reads_the_real_goals_or_the_canary_customer(real):
    r = real.get("/owner/graph/search", params={"q": "canary"}, headers=AGENT)
    assert r.status_code == 200 and r.json()["nodes"] == []
    schema = real.get("/owner/schema", headers=AGENT).json()
    locked = {x["label"] for x in schema["labels"] if x.get("locked")}
    assert {"Goal", "KnowledgeGap", "Customer"} <= locked
    assert real.get("/owner/graph/search", params={"label": "Goal"},
                    headers=AGENT).status_code == 403


def test_agent_tags_a_real_dish_then_the_owner_confirms_the_badge(real, conn):
    item = scalar(conn, "SELECT n.id FROM kg.node n WHERE n.label='MenuItem' AND NOT EXISTS"
                  " (SELECT 1 FROM kg.edge e WHERE e.src=n.id AND e.type='SUITABLE_FOR')"
                  " ORDER BY n.id LIMIT 1")
    r = post(real, "create_edge", f"{item}|SUITABLE_FOR|diet_vegan",
             {"src": item, "dst": "diet_vegan", "type": "SUITABLE_FOR"}, "no animal products")
    assert r.status_code == 200 and (r.json()["tier"], r.json()["state"]) == ("auto", "applied")
    assert scalar(conn, "SELECT verified_by_owner FROM kg_public.edge WHERE src=%s AND"
                  " dst='diet_vegan'", item) is False
    edge_id = scalar(conn, "SELECT id FROM kg.edge WHERE src=%s AND dst='diet_vegan'", item)
    assert real.post("/owner/verify", headers=OWNER, json={"edge_ids": [edge_id]}).status_code \
        == 200
    assert scalar(conn, "SELECT verified_by_owner FROM kg_public.edge WHERE src=%s AND"
                  " dst='diet_vegan'", item) is True


def test_gift_card_loop_on_the_real_registry(real, conn):
    steps = [
        post(real, "create_label", "GiftCard", {"may_be_public": True,
             "public_props": ["amounts", "terms"], "description": "Gift cards"}),
        post(real, "create_node", "gc_25", {"label": "GiftCard", "name": "$25 gift card",
             "props": {"amounts": "25", "terms": "No expiry"}}),
        post(real, "create_node", "gc_50", {"label": "GiftCard", "name": "$50 gift card",
             "props": {"amounts": "50", "terms": "No expiry"}}),
        post(real, "create_component", "ui_form_gift_card", FORM),
    ]
    assert [s.json()["state"] for s in steps] == ["pending"] * 4, [s.text for s in steps]
    for s in steps:
        assert decide(real, s.json()["change_id"], "approve").status_code == 200
    assert scalar(conn, "SELECT count(*) FROM kg_public.node WHERE label='GiftCard'") == 2
    comp = scalar(conn, "SELECT props FROM kg_public.node WHERE id='ui_form_gift_card'")
    assert comp["primitive"] == "FormCard" and comp["fields"][0]["name"] == "recipient"
    assert comp["selectable"] is True and comp["use_when"].startswith("Visitor asks")


def test_edit_a_real_dish_approve_then_revert(real, conn):
    item = scalar(conn, "SELECT id FROM kg.node WHERE label='MenuItem' AND props ? 'description'"
                  " ORDER BY id LIMIT 1")
    old = scalar(conn, "SELECT props->>'description' FROM kg.node WHERE id=%s", item)
    ch = post(real, "update_node", item, {"props": {"description": "Now with truffle"}}).json()
    assert ch["state"] == "pending"
    assert decide(real, ch["change_id"], "approve").status_code == 200
    assert scalar(conn, "SELECT props->>'description' FROM kg_public.node WHERE id=%s",
                  item) == "Now with truffle"
    assert decide(real, ch["change_id"], "revert").status_code == 200
    assert scalar(conn, "SELECT props->>'description' FROM kg_public.node WHERE id=%s",
                  item) == old


def test_parking_gap_loop_on_the_real_graph(real, conn):
    seed_traffic.seed(conn, "biz_demo")
    conn.commit()
    gaps = {g["topic"]: g for g in real.get("/owner/gaps", headers=AGENT).json()}
    assert gaps["parking"]["count"] == 5 and gaps["gift cards"]["count"] == 12
    assert real.post(f"/owner/gaps/{gaps['parking']['gap_id']}/asked",
                     headers=AGENT).status_code == 200
    words = "There is a garage at 1 Kenmore Sq, and street parking is free after 6pm."
    ans = real.post("/owner/answers", headers=AGENT,
                    json={"gap_id": gaps["parking"]["gap_id"], "answer_text": words})
    assert ans.status_code == 200
    assert real.post("/owner/publish", headers=AGENT).status_code == 200
    faq = scalar(conn, "SELECT props FROM kg_public.node WHERE id=%s", ans.json()["faq"])
    assert faq["answer"] == words
    assert scalar(conn, "SELECT verified_by_owner FROM kg_public.node WHERE id=%s",
                  ans.json()["faq"]) is True
    assert scalar(conn, "SELECT count(*) FROM kg_public.edge WHERE src=%s AND dst='biz_demo'"
                  " AND type='ANSWERS'", ans.json()["faq"]) == 1


def test_special_hours_on_the_real_graph(real, conn):
    r = real.post("/owner/special-hours", headers=AGENT, json={
        "date": "2026-12-24", "closed": False, "opens": "11:00", "closes": "18:00"})
    assert r.status_code == 200
    assert real.post("/owner/publish", headers=AGENT).status_code == 200
    assert scalar(conn, "SELECT verified_by_owner FROM kg_public.node"
                  " WHERE id='sh_2026_12_24'") is True
    assert scalar(conn, "SELECT count(*) FROM kg_public.edge WHERE dst='sh_2026_12_24'"
                  " AND type='HAS_HOURS'") == 1


def test_the_serving_role_still_cannot_read_what_the_owner_wrote(pg, real):
    with psycopg.connect(pg["serve"]) as serve:
        for table in ("kg.node", "kg.change", "ops.lead"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                serve.execute(f"SELECT * FROM {table} LIMIT 1")
            serve.rollback()
