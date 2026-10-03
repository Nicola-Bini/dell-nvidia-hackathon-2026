"""wp8, Serve side: owner-side changes take effect on the next request, with no restart.

The Serve API runs as its own process throughout. Graph changes are written the way the
Owner tools API writes them (see graph_writes.py), then published.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from e2e_support import ask, components
from graph_writes import add_edge, add_label, add_node, publish, remove

pytestmark = pytest.mark.e2e

KIDS_QUESTION = "do you have a kids menu?"
KIDS_ANSWER = "Yes. Kids eat for $6.95 until 8pm."
KIDS_FAQ = {"id": "faq_e2e_kids_menu", "label": "FAQ", "name": "Do you have a kids menu?",
            "props": {"question": "Do you have a kids menu?", "answer": KIDS_ANSWER},
            "source_type": "owner", "verified": True}

GIFT_TERMS = "Valid for 12 months. Redeemable in the bar."
GIFT_NODES = [
    {"id": "gc_e2e_25", "label": "GiftCard", "name": "$25 gift card",
     "props": {"amounts": "$25", "terms": GIFT_TERMS}},
    {"id": "gc_e2e_50", "label": "GiftCard", "name": "$50 gift card",
     "props": {"amounts": "$50", "terms": GIFT_TERMS}},
]
GIFT_FORM = {"id": "ui_form_gift_card", "label": "UIComponent", "name": "Request a gift card",
             "props": {
                 "component": "FormCard", "primitive": "FormCard", "version": 1,
                 "use_when": "Visitor wants to buy or request a gift card.",
                 "binds": {"labels": ["Service"], "min": 0, "max": 1}, "selectable": True,
                 "preset": None, "cta_label": None, "rail_label": "Request a gift card",
                 "say": None, "chips": ["See the menu"], "channels": ["web", "mcp"],
                 "submit_label": "Send request",
                 "fields": [
                     {"name": "name", "type": "text", "label": "Your name", "required": True},
                     {"name": "contact", "type": "text", "label": "Email or phone",
                      "required": True},
                     {"name": "amount", "type": "select", "label": "Amount", "required": True,
                      "options": ["$25", "$50"]}]}}


def last_log(owner_db, session_id: str) -> tuple:
    return owner_db.execute(
        "SELECT channel, kind, gap_topic, cache FROM ops.intent_log"
        " WHERE session_id = %s ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()


def test_gap_loop_without_restart(serve, owner_db, settings, session_id):
    """SCHEMA section 10 "Gap loop": unknown question -> gap; after the owner's answer and
    a publish, the same question returns Answer with verified true."""
    remove(owner_db, settings.business_id, [KIDS_FAQ["id"]])
    try:
        before = ask(serve, KIDS_QUESTION, session_id)
        assert before["kind"] == "gap"
        channel, kind, topic, _ = last_log(owner_db, session_id)
        assert (channel, kind) == ("web", "gap")
        assert topic

        add_node(owner_db, settings.business_id, KIDS_FAQ)
        add_edge(owner_db, settings.business_id, (KIDS_FAQ["id"], settings.business_id,
                                                  "ANSWERS"))
        version = publish(owner_db, settings.business_id)

        after = ask(serve, KIDS_QUESTION, session_id)
        assert after["kind"] == "answer"
        assert after["meta"]["graph_version"] == version
        answer = after["views"][0]
        assert answer["component"] == "Answer"
        assert answer["data"]["answer"] == KIDS_ANSWER
        assert answer["data"]["verified"] is True
    finally:
        remove(owner_db, settings.business_id, [KIDS_FAQ["id"]])


def test_agent_adds_a_node_type_and_a_form_without_restart(serve, owner_db, settings,
                                                           session_id):
    """Section 10 "Agent adds a node type" and "Agent adds an element": after approval and
    publish, the question returns a ListCard of the new nodes and the new form, and a
    submit stores a `form` lead."""
    ids = [node["id"] for node in GIFT_NODES] + [GIFT_FORM["id"]]
    remove(owner_db, settings.business_id, ids, labels=("GiftCard",))
    try:
        add_label(owner_db, "GiftCard", ["amounts", "terms"])
        for node in [*GIFT_NODES, GIFT_FORM]:
            add_node(owner_db, settings.business_id, node)
        publish(owner_db, settings.business_id)

        surface = ask(serve, "do you sell gift cards?", session_id)
        assert surface["kind"] == "answer"
        assert components(surface)[:2] == ["ListCard", "FormCard"]
        listed = [item["id"] for item in surface["views"][0]["data"]["items"]]
        assert listed == ["gc_e2e_25", "gc_e2e_50"]
        assert surface["views"][1]["data"]["form"] == "ui_form_gift_card"

        submit = serve.post("/v1/action", json={
            "name": "submit_form", "session_id": session_id, "component": "ui_form_gift_card",
            "payload": {"form": "ui_form_gift_card",
                        "values": {"name": "E2E Guest", "contact": "e2e@example.invalid",
                                   "amount": "$50"}}})
        assert submit.status_code == 200
        lead = owner_db.execute(
            "SELECT kind, component, payload -> 'values' ->> 'amount' FROM ops.lead"
            " WHERE id = %s", (submit.json()["lead_id"],)).fetchone()
        assert lead == ("form", "ui_form_gift_card", "$50")
    finally:
        remove(owner_db, settings.business_id, ids, labels=("GiftCard",))


def test_prewarm_channel_fills_the_cache(serve, owner_db, settings, session_id):
    """Publish pre-warm (OWNERSHIP seam 5): a loopback caller may set X-CAC-Channel, the
    request is logged as `prewarm`, and the visitor's first ask is then a cache hit."""
    publish(owner_db, settings.business_id)  # a new version: nothing cached yet
    question = "what's on draft?"
    warmed = ask(serve, question, session_id, headers={"X-CAC-Channel": "prewarm"})
    assert warmed["meta"]["cache"] == "miss"
    assert last_log(owner_db, session_id)[0] == "prewarm"
    visitor = ask(serve, question, session_id)
    assert visitor["meta"]["cache"] == "exact"
    assert last_log(owner_db, session_id)[0] == "web"
    assert visitor["views"] == warmed["views"]


def test_widget_is_served_once_it_is_built(serve):
    dist = Path(__file__).resolve().parents[2] / "apps" / "widget" / "dist"
    if not (dist / "index.html").is_file():
        pytest.skip("apps/widget/dist is not built yet (cj's lane)")
    assert serve.get("/widget/").status_code == 200
    assert serve.get("/embed.js").status_code == 200
