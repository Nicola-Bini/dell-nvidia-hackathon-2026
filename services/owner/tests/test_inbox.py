"""wp4: the owner's inbox page and its JSON twin."""

from psycopg.types.json import Jsonb

from tests.conftest import AGENT, OWNER
from tests.test_change_engine import post, scalar

XSS = "<script>alert(1)</script>"


def seed_inbox(client, db):
    pending = post(client, "update_node", "mi_risotto", {"props": {"description": "Wild"}},
                   "Site copy changed <b>bold</b>",
                   evidence={"topic": "risotto", "count": 3}).json()
    post(client, "create_edge", "k", {"src": "mi_risotto", "dst": "diet_vegan",
                                       "type": "SUITABLE_FOR"}, "No meat")
    db.execute("INSERT INTO ops.lead (id, business_id, kind, component, payload, channel)"
               " VALUES (gen_random_uuid(), 'biz_demo', 'booking_request', 'BookingForm', %s,"
               " 'web')", (Jsonb({"name": XSS, "party_size": 4}),))
    db.execute("INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
               " source_type) VALUES ('gap_parking', 'biz_demo', 'KnowledgeGap', 'parking', %s,"
               " 'private', 'approved', 'agent')",
               (Jsonb({"topic": "parking", "count": 5, "sessions": 4, "state": "open"}),))
    db.commit()
    return pending


def test_inbox_json_has_every_section(client, db):
    pending = seed_inbox(client, db)
    data = client.get("/owner/inbox.json", headers=OWNER).json()
    assert set(data) == {"pending", "unverified_tags", "applied", "leads", "gaps"}

    item = data["pending"][0]
    assert item["change_id"] == pending["change_id"] and item["action"] == "update_node"
    assert item["reason"].startswith("Site copy") and item["evidence"]["count"] == 3
    assert item["before"]["props"]["description"] == "Arborio rice, mushrooms"
    assert item["after"]["props"]["description"] == "Wild"

    tags = {(t["src"], t["dst"]) for t in data["unverified_tags"]}
    assert ("mi_risotto", "diet_vegan") in tags
    tag = next(t for t in data["unverified_tags"] if t["dst"] == "diet_vegan")
    assert tag["src_name"] == "Mushroom Risotto" and tag["dst_name"] == "Vegan"
    assert isinstance(tag["edge_id"], int)

    assert data["applied"][0]["action"] == "create_edge"
    assert data["leads"][0]["payload"]["party_size"] == 4
    assert data["gaps"] == [{"gap_id": "gap_parking", "topic": "parking", "count": 5,
                             "state": "open"}]


def test_confirming_a_tag_removes_it_from_the_inbox(client, db):
    seed_inbox(client, db)
    tag = next(t for t in client.get("/owner/inbox.json", headers=OWNER).json()["unverified_tags"]
               if t["dst"] == "diet_vegan")
    client.post("/owner/verify", headers=OWNER, json={"edge_ids": [tag["edge_id"]]})
    after = client.get("/owner/inbox.json", headers=OWNER).json()["unverified_tags"]
    assert all(t["edge_id"] != tag["edge_id"] for t in after)


def test_inbox_page_is_html_with_buttons_and_escapes_everything(client, db):
    seed_inbox(client, db)
    r = client.get("/owner/inbox", headers=OWNER)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    for word in ("Pending changes", "Unverified tags", "Applied changes", "New leads",
                 "Open gaps", "Approve", "Reject", "Confirm", "Revert"):
        assert word in html, word
    assert "Site copy changed" in html and "&lt;b&gt;bold&lt;/b&gt;" in html
    assert XSS not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>bold</b>" not in html
    assert "owner-secret" not in html


def test_inbox_refuses_the_agent_and_strangers(client):
    assert client.get("/owner/inbox", headers=AGENT).status_code == 403
    assert client.get("/owner/inbox").status_code == 401
    assert client.get("/owner/inbox.json").status_code == 401
    assert client.get("/owner/inbox?token=wrong").status_code == 401
    assert client.get("/owner/inbox?token=agent-secret").status_code == 401


def test_token_in_the_url_becomes_a_cookie_and_is_removed_from_the_address(client):
    r = client.get("/owner/inbox?token=owner-secret", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/owner/inbox"
    cookie = r.headers["set-cookie"].lower()
    assert "cac_inbox=owner-secret" in cookie and "httponly" in cookie
    assert "samesite=strict" in cookie
    assert client.get("/owner/inbox").status_code == 200  # the cookie jar kept it


def test_cookie_writes_need_the_csrf_header(client, db):
    ch = post(client, "update_node", "mi_risotto", {"props": {"description": "Wild"}}).json()
    client.get("/owner/inbox?token=owner-secret")
    url = f"/owner/changes/{ch['change_id']}/approve"
    assert client.post(url).status_code == 403
    assert scalar(db, "SELECT state FROM kg.change WHERE id=%s", ch["change_id"]) == "pending"
    assert client.post(url, headers={"X-Requested-With": "cac-inbox"}).status_code == 200


def test_the_inbox_cookie_is_not_the_agent(client):
    client.get("/owner/inbox?token=owner-secret")
    r = client.post("/owner/changes", json={"action": "update_node", "target": "mi_risotto",
                                            "after": {}, "reason": "x"},
                    headers={"X-Requested-With": "cac-inbox"})
    assert r.status_code == 403
