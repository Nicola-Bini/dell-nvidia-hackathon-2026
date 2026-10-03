"""wp4: approve, reject, revert, verify. SCHEMA section 10: 'Agent adds a node type',
'Agent adds an element', 'Agent edits a dish', and the verified-badge half of 'Agent tags a
dish'."""

from tests.conftest import AGENT, OWNER
from tests.test_change_engine import FORM, post, scalar


def decide(client, change_id, verb, **body):
    return client.post(f"/owner/changes/{change_id}/{verb}", headers=OWNER, json=body or None)


# --- Agent adds a node type ---------------------------------------------------------------------

def test_agent_adds_a_node_type_and_it_reaches_the_public_side_after_approval(client, db):
    label = post(client, "create_label", "GiftCard", {"may_be_public": True,
                 "public_props": ["amounts", "terms"], "description": "Gift cards"},
                 "12 visitors asked", evidence={"topic": "gift cards", "count": 12}).json()
    nodes = [post(client, "create_node", nid, {"label": "GiftCard", "name": name,
              "props": {"amounts": amt, "terms": "Valid a year", "internal_cost": 1}},
                  "gift card options").json()
             for nid, name, amt in (("gc_25", "$25 gift card", "25"),
                                    ("gc_50", "$50 gift card", "50"))]
    assert {x["state"] for x in [label, *nodes]} == {"pending"}
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE label='GiftCard'") == 0

    for change in [label, *nodes]:
        r = decide(client, change["change_id"], "approve")
        assert r.status_code == 200 and r.json()["state"] == "applied"
        assert r.json()["graph_version"] >= 2

    rows = db.execute("SELECT id, props, verified_by_owner FROM kg_public.node"
                      " WHERE label='GiftCard' ORDER BY id").fetchall()
    assert [r["id"] for r in rows] == ["gc_25", "gc_50"]
    assert rows[0]["props"] == {"amounts": "25", "terms": "Valid a year"}
    assert all(r["verified_by_owner"] is False for r in rows)
    decided = db.execute("SELECT state, decided_by, decided_at FROM kg.change WHERE id=%s",
                         (label["change_id"],)).fetchone()
    assert decided["state"] == "applied" and decided["decided_by"] == "owner"
    assert decided["decided_at"] is not None


def test_approving_the_nodes_before_the_label_publishes_nothing_yet(client, db):
    label = post(client, "create_label", "GiftCard", {"may_be_public": True,
                 "public_props": ["amounts"]}).json()
    node = post(client, "create_node", "gc_25", {"label": "GiftCard", "name": "$25",
                "props": {"amounts": "25"}}).json()
    decide(client, node["change_id"], "approve")
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE label='GiftCard'") == 0
    decide(client, label["change_id"], "approve")
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE label='GiftCard'") == 1


# --- Agent adds an element ----------------------------------------------------------------------

def test_agent_adds_an_element_and_it_is_published_on_approval(client, db):
    ch = post(client, "create_component", "ui_form_gift_card", FORM, "demand",
              evidence={"topic": "gift cards", "count": 12}).json()
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='ui_form_gift_card'") == 0
    assert decide(client, ch["change_id"], "approve").status_code == 200
    props = scalar(db, "SELECT props FROM kg_public.node WHERE id='ui_form_gift_card'")
    assert props["primitive"] == "FormCard" and props["fields"][0]["name"] == "recipient"
    assert props["selectable"] is True


# --- Agent edits a dish -------------------------------------------------------------------------

def test_edit_is_pending_then_approved_then_reverted_to_the_old_text(client, db):
    old = "Arborio rice, mushrooms"
    ch = post(client, "update_node", "mi_risotto", {"props": {"description": "Wild mushrooms"}},
              "site copy changed").json()
    assert ch["state"] == "pending"
    assert scalar(db, "SELECT props->>'description' FROM kg_public.node"
                  " WHERE id='mi_risotto'") == old

    assert decide(client, ch["change_id"], "approve").status_code == 200
    assert scalar(db, "SELECT props->>'description' FROM kg.node WHERE id='mi_risotto'") \
        == "Wild mushrooms"
    assert scalar(db, "SELECT props->>'description' FROM kg_public.node"
                  " WHERE id='mi_risotto'") == "Wild mushrooms"

    r = decide(client, ch["change_id"], "revert")
    assert r.status_code == 200 and r.json()["state"] == "reverted"
    assert scalar(db, "SELECT props->>'description' FROM kg.node WHERE id='mi_risotto'") == old
    assert scalar(db, "SELECT props->>'description' FROM kg_public.node"
                  " WHERE id='mi_risotto'") == old
    assert "Arborio" in scalar(db, "SELECT search_text FROM kg.node WHERE id='mi_risotto'")
    assert scalar(db, "SELECT state FROM kg.change WHERE id=%s", ch["change_id"]) == "reverted"


def test_rejected_edit_never_applies_and_the_agent_sees_the_reason(client, db):
    ch = post(client, "update_node", "mi_risotto", {"props": {"description": "Bad"}}).json()
    r = decide(client, ch["change_id"], "reject", reason="Not what we serve")
    assert r.status_code == 200 and r.json()["state"] == "rejected"
    assert scalar(db, "SELECT props->>'description' FROM kg.node WHERE id='mi_risotto'") \
        == "Arborio rice, mushrooms"
    seen = client.get("/owner/changes", params={"state": "rejected"}, headers=AGENT).json()
    assert seen[0]["evidence"]["rejection_reason"] == "Not what we serve"


def test_rejected_new_node_is_retired_and_never_published(client, db):
    ch = post(client, "create_node", "faq_x", {"label": "FAQ", "name": "X"}).json()
    decide(client, ch["change_id"], "reject")
    assert scalar(db, "SELECT status FROM kg.node WHERE id='faq_x'") == "retired"
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='faq_x'") == 0


def test_reverting_a_created_node_retires_it(make_client, db):
    c = make_client(autonomy="free")
    ch = post(c, "create_node", "faq_x", {"label": "FAQ", "name": "X"}).json()
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='faq_x'") == 1
    assert decide(c, ch["change_id"], "revert").status_code == 200
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='faq_x'") == 0


def test_reverting_a_retired_edge_restores_it(make_client, db):
    c = make_client(autonomy="free")
    post(c, "create_edge", "k", {"src": "mi_risotto", "dst": "diet_vegan", "type": "SUITABLE_FOR"})
    ch = post(c, "retire_edge", "mi_risotto|SUITABLE_FOR|diet_vegan").json()
    assert scalar(db, "SELECT count(*) FROM kg_public.edge WHERE dst='diet_vegan'") == 0
    decide(c, ch["change_id"], "revert")
    assert scalar(db, "SELECT count(*) FROM kg_public.edge WHERE dst='diet_vegan'") == 1


def test_reverting_add_prop_restores_the_allowlist(make_client, db):
    c = make_client(autonomy="free")
    ch = post(c, "add_prop", "MenuItem", {"prop": "spice_level"}).json()
    decide(c, ch["change_id"], "revert")
    assert "spice_level" not in scalar(db, "SELECT public_props FROM kg.label"
                                       " WHERE label='MenuItem'")


# --- decisions are owner-only and state-checked --------------------------------------------------

def test_the_agent_token_is_refused_on_every_owner_action(client):
    ch = post(client, "update_node", "mi_risotto", {"props": {"description": "x"}}).json()
    cid = ch["change_id"]
    for path, body in ((f"/owner/changes/{cid}/approve", None),
                       (f"/owner/changes/{cid}/reject", None),
                       (f"/owner/changes/{cid}/revert", None),
                       ("/owner/verify", {"node_ids": ["mi_risotto"]})):
        r = client.post(path, headers=AGENT, json=body)
        assert r.status_code == 403, path
        assert r.json()["detail"]["tier"] == "locked"
    assert client.get("/owner/inbox.json", headers=AGENT).status_code == 403


def test_state_machine_conflicts(client):
    ch = post(client, "update_node", "mi_risotto", {"props": {"description": "x"}}).json()
    cid = ch["change_id"]
    assert decide(client, cid, "revert").status_code == 409        # not applied yet
    assert decide(client, cid, "approve").status_code == 200
    assert decide(client, cid, "approve").status_code == 409       # already applied
    assert decide(client, cid, "reject").status_code == 409
    assert decide(client, cid, "revert").status_code == 200
    assert decide(client, cid, "revert").status_code == 409
    assert decide(client, 9999, "approve").status_code == 404


def test_locked_changes_cannot_be_approved(client):
    r = post(client, "update_node", "mi_caprese", {"verified_by_owner": True})
    assert decide(client, r.json()["change_id"], "approve").status_code == 409


# --- verify: the only road to a badge ------------------------------------------------------------

def test_verify_an_edge_publishes_the_badge(client, db):
    post(client, "create_edge", "k", {"src": "mi_risotto", "dst": "diet_vegetarian",
                                       "type": "SUITABLE_FOR"})
    edge_id = scalar(db, "SELECT id FROM kg.edge WHERE src='mi_risotto' AND dst='diet_vegetarian'")
    assert scalar(db, "SELECT verified_by_owner FROM kg_public.edge WHERE src='mi_risotto'"
                  " AND dst='diet_vegetarian'") is False
    r = client.post("/owner/verify", headers=OWNER, json={"edge_ids": [edge_id]})
    assert r.status_code == 200 and r.json()["verified_edges"] == 1
    assert scalar(db, "SELECT verified_by_owner FROM kg_public.edge WHERE src='mi_risotto'"
                  " AND dst='diet_vegetarian'") is True
    row = db.execute("SELECT verified_by_owner, verified_at FROM kg.edge WHERE id=%s",
                     (edge_id,)).fetchone()
    assert row["verified_by_owner"] is True and row["verified_at"] is not None


def test_verify_a_node(client):
    r = client.post("/owner/verify", headers=OWNER, json={"node_ids": ["mi_risotto"]})
    assert r.status_code == 200 and r.json()["verified_nodes"] == 1


def test_verify_needs_ids_and_rejects_unknown(client):
    assert client.post("/owner/verify", headers=OWNER, json={}).status_code == 422
    assert client.post("/owner/verify", headers=OWNER,
                       json={"node_ids": ["nope"]}).status_code == 404
