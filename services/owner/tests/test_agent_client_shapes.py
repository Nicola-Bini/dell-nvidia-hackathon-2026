"""The agent's client (agent/cac_owner.py, agent/plans/gift_card.json) posts shapes that differ
from the SCHEMA text: object targets, string evidence, flat node props, fields as names.
The API accepts both; the stored change records use the SCHEMA shapes."""

import json
import pathlib

from tests.conftest import AGENT

PLAN = pathlib.Path(__file__).resolve().parents[3] / "agent" / "plans" / "gift_card.json"


def post(client, change, reason="r", evidence="12 visitors in 9 sessions asked about gift cards"):
    return client.post("/owner/changes", headers=AGENT, json={
        **change, "reason": reason, "evidence": evidence})


def test_nicos_gift_card_plan_goes_through_in_balanced_mode(client, db):
    plan = json.loads(PLAN.read_text())
    results = [post(client, ch, plan["reason"].format(topic="gift cards"))
               for ch in plan["changes"]]
    assert [r.status_code for r in results] == [200, 200, 200, 200], [r.text for r in results]
    assert [r.json()["state"] for r in results] == ["pending"] * 4
    nodes = db.execute("SELECT id, label, props, status FROM kg.node WHERE id LIKE 'gc_%'"
                       " ORDER BY id").fetchall()
    assert [n["id"] for n in nodes] == ["gc_25", "gc_50"]
    assert nodes[0]["props"] == {"amounts": "25", "terms": "Pending owner confirmation"}
    comp = db.execute("SELECT id, name, props FROM kg.node WHERE label='UIComponent'"
                      " AND id <> 'ui_faq'").fetchone()
    assert comp["id"] == "ui_gift_card_request" and comp["name"] == "GiftCardRequest"
    assert comp["props"]["primitive"] == "FormCard"
    assert [f["name"] for f in comp["props"]["fields"]] == ["name", "email", "amount"]
    assert comp["props"]["submit_label"] == "Request a gift card"


def test_string_evidence_is_stored_as_an_object(client, db):
    r = post(client, {"action": "create_label", "target": {"label": "GiftCard"},
                      "after": {"may_be_public": True}})
    ev = db.execute("SELECT evidence FROM kg.change WHERE id=%s",
                    (r.json()["change_id"],)).fetchone()["evidence"]
    assert ev == {"text": "12 visitors in 9 sessions asked about gift cards"}


def test_object_target_for_an_edge(client, db):
    r = post(client, {"action": "create_edge",
                      "target": {"src": "mi_risotto", "dst": "diet_vegan", "type": "SUITABLE_FOR"},
                      "after": {}})
    assert r.status_code == 200 and r.json()["state"] == "applied"


def test_object_target_for_add_prop_and_update_node(client):
    r = post(client, {"action": "add_prop", "target": {"label": "MenuItem"},
                      "after": {"prop": "spice_level"}})
    assert r.status_code == 200
    r = post(client, {"action": "update_node", "target": {"node_id": "mi_risotto"},
                      "after": {"description": "Wild mushrooms"}})
    assert r.status_code == 200 and r.json()["state"] == "pending"


def test_unknown_target_object_is_422(client):
    r = post(client, {"action": "create_label", "target": {"nope": 1}, "after": {}})
    assert r.status_code == 422
