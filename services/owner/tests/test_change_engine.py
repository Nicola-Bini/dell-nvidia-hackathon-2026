"""wp3: POST /owner/changes. SCHEMA section 10 'Agent tags a dish' and 'Agent tries the
locked tier', plus every action and the tier-dependent apply paths."""

from tests.conftest import AGENT, OWNER


def post(client, action, target, after=None, reason="because", evidence=None, headers=AGENT):
    return client.post("/owner/changes", headers=headers, json={
        "action": action, "target": target, "after": after or {}, "reason": reason,
        "evidence": evidence or {}})


def scalar(db, sql, *args):
    row = db.execute(sql, args).fetchone()
    return None if row is None else next(iter(row.values()))


def edge_status(db, src, dst, typ):
    return scalar(db, "SELECT status FROM kg.edge WHERE src=%s AND dst=%s AND type=%s",
                  src, dst, typ)


TAG = {"src": "mi_risotto", "dst": "diet_vegetarian", "type": "SUITABLE_FOR"}


# --- SCHEMA 10: Agent tags a dish -------------------------------------------------------------

def test_agent_tags_a_dish_auto_in_balanced_and_publishes_unverified(client, db):
    r = post(client, "create_edge", "mi_risotto|SUITABLE_FOR|diet_vegetarian", TAG,
             "No meat or fish in the description", {"topic": "vegetarian", "count": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "auto" and body["state"] == "applied" and body["change_id"] > 0
    row = db.execute("SELECT status, source_type, verified_by_owner FROM kg.edge WHERE"
                     " src='mi_risotto' AND dst='diet_vegetarian'").fetchone()
    assert row == {"status": "approved", "source_type": "agent", "verified_by_owner": False}
    pub = db.execute("SELECT verified_by_owner FROM kg_public.edge WHERE src='mi_risotto'"
                     " AND type='SUITABLE_FOR'").fetchone()
    assert pub == {"verified_by_owner": False}
    ch = db.execute("SELECT actor, tier, state, reason, evidence FROM kg.change WHERE id=%s",
                    (body["change_id"],)).fetchone()
    assert ch["actor"] == "agent" and ch["evidence"] == {"topic": "vegetarian", "count": 4}


def test_tag_is_one_tap_in_cautious_mode_and_stays_off_the_public_side(make_client, db):
    c = make_client(autonomy="cautious")
    r = post(c, "create_edge", "mi_risotto|SUITABLE_FOR|diet_vegan",
             {"src": "mi_risotto", "dst": "diet_vegan", "type": "SUITABLE_FOR"})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    assert edge_status(db, "mi_risotto", "diet_vegan", "SUITABLE_FOR") == "draft"
    assert scalar(db, "SELECT count(*) FROM kg_public.edge WHERE dst='diet_vegan'") == 0


def test_agent_cannot_choose_the_tier_or_the_provenance(client, db):
    r = post(client, "create_edge", "x", {"src": "mi_risotto", "dst": "diet_vegan",
             "type": "SUITABLE_FOR", "tier": "auto", "source_type": "owner"})
    assert r.status_code == 200
    assert scalar(db, "SELECT source_type FROM kg.edge WHERE dst='diet_vegan'") == "agent"


# --- SCHEMA 10: Agent tries the locked tier -----------------------------------------------------

def test_setting_verified_is_refused_and_recorded(client, db):
    r = post(client, "update_node", "mi_caprese", {"verified_by_owner": True})
    assert r.status_code == 403
    body = r.json()
    assert body["tier"] == "locked" and body["state"] == "rejected" and "reason" in body
    assert scalar(db, "SELECT tier FROM kg.change WHERE id=%s", body["change_id"]) == "locked"


def test_verified_on_an_edge_is_refused(client, db):
    r = post(client, "create_edge", "k", {**TAG, "verified_by_owner": True})
    assert r.status_code == 403
    assert edge_status(db, "mi_risotto", "diet_vegetarian", "SUITABLE_FOR") is None


def test_verified_hidden_in_props_is_refused(client):
    r = post(client, "create_node", "faq_x", {"label": "FAQ", "name": "x",
             "props": {"verified_by_owner": True}})
    assert r.status_code == 403


def test_writing_a_customer_or_goal_is_refused(client, db):
    for node in ("cust_canary", "goal_bookings"):
        assert post(client, "update_node", node, {"name": "pwned"}).status_code == 403, node
    assert scalar(db, "SELECT name FROM kg.node WHERE id='cust_canary'") == "ZZ-CANARY-Customer"


def test_creating_a_locked_label_or_node_is_refused(client):
    assert post(client, "create_label", "Customer", {"may_be_public": True}).status_code == 403
    assert post(client, "create_label", "goal", {}).status_code == 403
    r = post(client, "create_node", "goal_new", {"label": "Goal", "name": "g"})
    assert r.status_code == 403


def test_an_edge_to_a_goal_is_refused(client):
    r = post(client, "create_edge", "k", {"src": "mi_risotto", "dst": "goal_bookings",
                                           "type": "ADVANCES"})
    assert r.status_code == 403


def test_approve_with_the_agent_token_is_refused(client):
    assert post(client, "update_node", "mi_risotto", {"name": "Z"}).status_code == 200
    assert client.post("/owner/changes/1/approve", headers=AGENT).status_code == 403


def test_making_a_private_label_public_is_refused(client, db):
    r = post(client, "create_label", "Note", {"may_be_public": True})
    assert r.status_code in (403, 409)
    assert scalar(db, "SELECT may_be_public FROM kg.label WHERE label='Note'") is False


# --- the other actions -------------------------------------------------------------------------

def test_create_label_in_balanced_is_a_pending_draft(client, db):
    r = post(client, "create_label", "GiftCard", {"may_be_public": True,
             "public_props": ["amounts", "terms"], "description": "Gift cards"},
             "12 visitors asked", {"topic": "gift cards", "count": 12})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    row = db.execute("SELECT status, created_by, public_props FROM kg.label"
                     " WHERE label='GiftCard'").fetchone()
    assert row == {"status": "draft", "created_by": "agent", "public_props": ["amounts", "terms"]}


def test_create_label_private_is_auto(client, db):
    r = post(client, "create_label", "Supplier", {"may_be_public": False})
    assert (r.json()["tier"], r.json()["state"]) == ("auto", "applied")
    assert scalar(db, "SELECT status FROM kg.label WHERE label='Supplier'") == "approved"


def test_create_label_in_free_mode_is_live(make_client, db):
    r = post(make_client(autonomy="free"), "create_label", "GiftCard", {"may_be_public": True})
    assert r.json()["state"] == "applied"
    assert scalar(db, "SELECT status FROM kg.label WHERE label='GiftCard'") == "approved"


def test_create_existing_label_is_a_conflict(client):
    assert post(client, "create_label", "MenuItem", {}).status_code == 409


def test_add_prop_is_deferred_until_approval(client, db):
    r = post(client, "add_prop", "MenuItem", {"prop": "spice_level"})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    assert "spice_level" not in scalar(db, "SELECT public_props FROM kg.label"
                                       " WHERE label='MenuItem'")


def test_add_prop_free_mode_extends_the_allowlist(make_client, db):
    r = post(make_client(autonomy="free"), "add_prop", "MenuItem", {"prop": "spice_level"})
    assert r.json()["state"] == "applied"
    assert "spice_level" in scalar(db, "SELECT public_props FROM kg.label WHERE label='MenuItem'")
    before = scalar(db, "SELECT before FROM kg.change WHERE id=%s", r.json()["change_id"])
    assert "spice_level" not in before["public_props"]


def test_add_prop_to_an_unknown_label_is_422(client):
    assert post(client, "add_prop", "Nope", {"prop": "x"}).status_code == 422


def test_create_edge_type_pending_draft(client, db):
    r = post(client, "create_edge_type", "SEASONAL_IN", {"description": "Dish in a season"})
    assert r.json()["state"] == "pending"
    assert scalar(db, "SELECT status FROM kg.edge_type WHERE type='SEASONAL_IN'") == "draft"


def test_create_node_public_label_is_pending_draft_with_provenance(client, db):
    r = post(client, "create_node", "faq_parking", {"label": "FAQ", "name": "Parking",
             "props": {"question": "Parking?", "answer": "Street parking."},
             "source_type": "owner", "verified_by_owner": False})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    row = db.execute("SELECT status, source_type, verified_by_owner, visibility, search_text,"
                     " business_id FROM kg.node WHERE id='faq_parking'").fetchone()
    assert row["status"] == "draft" and row["source_type"] == "agent"
    assert row["verified_by_owner"] is False and row["business_id"] == "biz_demo"
    assert "Parking" in row["search_text"] and "Street parking" in row["search_text"]
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='faq_parking'") == 0


def test_create_node_free_mode_publishes_allowlisted_props_only(make_client, db):
    r = post(make_client(autonomy="free"), "create_node", "faq_parking",
             {"label": "FAQ", "name": "Parking", "props": {"answer": "Street", "supplier": "x"}})
    assert r.json()["state"] == "applied"
    pub = db.execute("SELECT props FROM kg_public.node WHERE id='faq_parking'").fetchone()
    assert pub["props"] == {"answer": "Street"}


def test_create_node_of_private_label_is_auto_and_not_public(client, db):
    r = post(client, "create_node", "note_1", {"label": "Note", "name": "n"})
    assert r.json()["state"] == "applied"
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='note_1'") == 0


def test_create_node_duplicate_or_bad_input(client):
    ok = {"label": "FAQ", "name": "x"}
    assert post(client, "create_node", "mi_risotto", {"label": "MenuItem",
                                                     "name": "x"}).status_code == 409
    assert post(client, "create_node", "x_1", {**ok, "label": "Nope"}).status_code == 422
    assert post(client, "create_node", "BAD ID", ok).status_code == 422
    assert post(client, "create_node", "faq_x", {"label": "FAQ"}).status_code == 422


def test_update_public_node_is_deferred_until_approval(client, db):
    r = post(client, "update_node", "mi_risotto", {"props": {"description": "New text"}})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    props = scalar(db, "SELECT props FROM kg.node WHERE id='mi_risotto'")
    assert props["description"] == "Arborio rice, mushrooms"
    snap = scalar(db, "SELECT before FROM kg.change WHERE id=%s", r.json()["change_id"])
    assert snap["props"]["description"] == "Arborio rice, mushrooms"


def test_update_node_free_mode_merges_props_and_reindexes(make_client, db):
    r = post(make_client(autonomy="free"), "update_node", "mi_risotto",
             {"props": {"description": "Wild mushroom risotto"}})
    assert r.json()["state"] == "applied"
    row = db.execute("SELECT props, search_text FROM kg.node WHERE id='mi_risotto'").fetchone()
    assert row["props"]["margin"] == 0.62 and row["props"]["description"].startswith("Wild")
    assert "Wild mushroom" in row["search_text"] and "0.62" not in row["search_text"]
    assert scalar(db, "SELECT props->>'description' FROM kg_public.node WHERE"
                  " id='mi_risotto'") == "Wild mushroom risotto"


def test_retire_node_free_mode_unpublishes(make_client, db):
    r = post(make_client(autonomy="free"), "retire_node", "mi_caprese")
    assert r.json()["state"] == "applied"
    assert scalar(db, "SELECT status FROM kg.node WHERE id='mi_caprese'") == "retired"
    assert scalar(db, "SELECT count(*) FROM kg_public.node WHERE id='mi_caprese'") == 0


def test_update_unknown_node_is_404(client):
    assert post(client, "update_node", "mi_nope", {"name": "x"}).status_code == 404


def test_create_edge_validates_ends_and_type(client):
    ok = {"src": "mi_risotto", "dst": "mi_caprese", "type": "PAIRS_WITH"}
    assert post(client, "create_edge", "k", {**ok, "dst": "mi_nope"}).status_code == 422
    assert post(client, "create_edge", "k", {**ok, "type": "NOPE"}).status_code == 422
    assert post(client, "create_edge", "k", ok).json()["state"] == "applied"
    assert post(client, "create_edge", "k", ok).status_code == 409


def test_pairs_with_is_auto_in_balanced_and_published(client, db):
    post(client, "create_edge", "k", {"src": "mi_risotto", "dst": "mi_caprese",
                                       "type": "PAIRS_WITH"})
    assert scalar(db, "SELECT count(*) FROM kg_public.edge WHERE type='PAIRS_WITH'") == 1


def test_retire_edge_is_auto_for_an_unverified_tag(client, db):
    post(client, "create_edge", "k", {"src": "mi_risotto", "dst": "diet_vegan",
                                       "type": "SUITABLE_FOR"})
    r = post(client, "retire_edge", "mi_risotto|SUITABLE_FOR|diet_vegan")
    assert r.json()["state"] == "applied"
    assert edge_status(db, "mi_risotto", "diet_vegan", "SUITABLE_FOR") == "retired"
    assert scalar(db, "SELECT count(*) FROM kg_public.edge WHERE dst='diet_vegan'") == 0


FORM = {"component": "GiftCardForm", "use_when": "Visitor asks about gift cards.",
        "primitive": "FormCard", "fields": [
            {"name": "recipient", "type": "text", "label": "Recipient", "required": True},
            {"name": "amount", "type": "select", "label": "Amount", "options": ["25", "50"]}]}


def test_create_component_is_pending_and_lands_as_a_ui_node(client, db):
    r = post(client, "create_component", "ui_form_gift_card", FORM, "gift card demand",
             {"topic": "gift cards", "count": 12})
    assert (r.json()["tier"], r.json()["state"]) == ("one_tap", "pending")
    row = db.execute("SELECT label, status, source_type, props FROM kg.node"
                     " WHERE id='ui_form_gift_card'").fetchone()
    assert row["label"] == "UIComponent" and row["status"] == "draft"
    assert row["props"]["primitive"] == "FormCard" and row["props"]["selectable"] is True


def test_create_component_validates_the_catalog_entry(client):
    bad_field = {**FORM, "fields": [{"name": "a", "type": "blob", "label": "A"}]}
    for bad in ({**FORM, "primitive": "BookingForm"}, {**FORM, "fields": []},
                {**FORM, "use_when": ""}, bad_field):
        assert post(client, "create_component", "ui_x", bad).status_code == 422


def test_update_component_is_deferred(client, db):
    post(client, "create_component", "ui_form_gift_card", FORM)
    db.execute("UPDATE kg.node SET status='approved' WHERE id='ui_form_gift_card'")
    db.commit()
    r = post(client, "update_component", "ui_form_gift_card", {"say": "Send a gift card."})
    assert r.json()["state"] == "pending"
    assert scalar(db, "SELECT props->>'say' FROM kg.node WHERE id='ui_form_gift_card'") is None


def test_request_validation(client):
    assert post(client, "drop_table", "x").status_code == 422
    assert post(client, "update_node", "mi_risotto", reason="").status_code == 422
    assert client.post("/owner/changes", json={"action": "update_node"},
                       headers=AGENT).status_code == 422
    assert post(client, "update_node", "mi_risotto", {"name": "x"}, headers={}).status_code == 401


def test_the_owner_token_is_not_the_agent_and_is_refused_here(client):
    assert post(client, "update_node", "mi_risotto", {"name": "X"}, headers=OWNER).status_code == 403


def test_openapi_documents_the_change_endpoint(client):
    assert "post" in client.get("/openapi.json").json()["paths"]["/owner/changes"]
