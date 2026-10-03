"""wp2: what the agent can read. Locked labels by name only; no leads, no visitor text."""

import json

import psycopg
from psycopg.types.json import Jsonb

from tests.conftest import AGENT, OWNER

CANARY = "ZZ-CANARY-Customer"


def body_text(resp) -> str:
    return json.dumps(resp.json())


def test_reads_need_a_token(client):
    for path in ("/owner/schema", "/owner/graph/search?q=a", "/owner/changes", "/owner/digest"):
        assert client.get(path).status_code == 401


def test_schema_lists_locked_labels_by_name_only(client):
    data = client.get("/owner/schema", headers=AGENT).json()
    by_name = {x["label"]: x for x in data["labels"]}
    assert by_name["Customer"] == {"label": "Customer", "locked": True}
    assert by_name["Goal"] == {"label": "Goal", "locked": True}
    assert by_name["MenuItem"]["public_props"][0] == "description"
    assert {e["type"] for e in data["edge_types"]} >= {"SUITABLE_FOR", "PAIRS_WITH"}


def test_schema_includes_catalog_entries(client, db):
    db.execute("INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
               " source_type) VALUES ('ui_faq', 'biz_demo', 'UIComponent', 'Answer',"
               " %s, 'public', 'approved', 'seed')", (Jsonb({"component": "Answer"}),))
    db.commit()
    data = client.get("/owner/schema", headers=AGENT).json()
    assert data["catalog"][0]["id"] == "ui_faq"


def test_search_never_returns_a_customer(client):
    for q in ("canary", CANARY, "ZZ-CANARY", "example.com"):
        r = client.get("/owner/graph/search", params={"q": q}, headers=AGENT)
        assert r.status_code == 200
        assert CANARY not in body_text(r) and r.json()["nodes"] == []


def test_search_never_returns_a_goal(client):
    r = client.get("/owner/graph/search", params={"q": "bookings"}, headers=AGENT)
    assert r.json()["nodes"] == []
    assert "goal_bookings" not in body_text(r)


def test_search_with_a_locked_label_is_refused(client):
    for label in ("Customer", "Goal", "KnowledgeGap"):
        r = client.get("/owner/graph/search", params={"label": label}, headers=AGENT)
        assert r.status_code == 403 and r.json()["detail"]["tier"] == "locked"


def test_search_returns_drafts_and_private_props_but_no_embedding(client):
    r = client.get("/owner/graph/search", params={"q": "risotto"}, headers=AGENT)
    node = r.json()["nodes"][0]
    assert node["id"] == "mi_risotto" and node["props"]["margin"] == 0.62
    assert "embedding" not in node and "search_text" not in node


def test_search_returns_edges_but_hides_edges_to_locked_nodes(client, db):
    db.execute("INSERT INTO kg.edge (business_id, src, dst, type, status, source_type)"
               " VALUES ('biz_demo', 'svc_reservations', 'goal_bookings', 'ADVANCES',"
               " 'approved', 'seed')")
    db.commit()
    r = client.get("/owner/graph/search", params={"q": "caprese"}, headers=AGENT)
    assert [e["dst"] for e in r.json()["edges"]] == ["diet_vegetarian"]
    r = client.get("/owner/graph/search", params={"label": "Service"}, headers=AGENT)
    assert r.json()["edges"] == []


def test_search_without_q_filters_by_label(client):
    r = client.get("/owner/graph/search", params={"label": "Diet"}, headers=AGENT)
    assert {n["id"] for n in r.json()["nodes"]} == {"diet_vegan", "diet_vegetarian"}


def test_changes_lists_only_agent_records(client, db):
    for actor in ("agent", "owner"):
        db.execute("INSERT INTO kg.change (business_id, actor, action, target, after, reason,"
                   " tier, state) VALUES ('biz_demo', %s, 'update_node', 'mi_risotto', %s,"
                   " 'why', 'one_tap', 'pending')", (actor, Jsonb({"name": "x"})))
    db.commit()
    rows = client.get("/owner/changes", params={"state": "pending"}, headers=AGENT).json()
    assert [r["actor"] for r in rows] == ["agent"]
    assert client.get("/owner/changes", params={"state": "applied"},
                      headers=AGENT).json() == []


def test_changes_rejects_unknown_state(client):
    assert client.get("/owner/changes", params={"state": "bogus"},
                      headers=AGENT).status_code == 422


def seed_traffic(db):
    db.execute("INSERT INTO ops.intent_log (business_id, channel, session_id, text, cache, kind,"
               " gap_topic, latency_ms, graph_version) VALUES"
               " ('biz_demo','web','s1','my name is ZZ-CANARY-Customer parking?','miss','gap',"
               " 'parking', 5, 1)")
    db.execute("INSERT INTO ops.lead (id, business_id, kind, component, payload, channel)"
               " VALUES (gen_random_uuid(), 'biz_demo', 'booking_request', 'BookingForm',"
               " %s, 'web')", (Jsonb({"name": "ZZ-CANARY-Customer"}),))
    db.commit()


def test_digest_is_counts_only(client, db):
    seed_traffic(db)
    r = client.get("/owner/digest", headers=AGENT)
    data = r.json()
    assert set(data) == {"questions_today", "top_topics", "open_gaps", "pending_changes",
                         "new_leads"}
    assert data["questions_today"] == 1
    assert data["new_leads"] == [{"kind": "booking_request", "count": 1}]
    assert CANARY not in body_text(r) and "canary@example.com" not in body_text(r)


def test_owner_token_gets_the_same_filtered_reads(client):
    r = client.get("/owner/graph/search", params={"q": "canary"}, headers=OWNER)
    assert r.status_code == 200 and r.json()["nodes"] == []
