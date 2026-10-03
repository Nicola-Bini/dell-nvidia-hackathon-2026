"""wp8, both services: the loops of SCHEMA section 10 through je's Owner tools API (SCHEMA
8.6) and the Serve API (8.5), over HTTP, with neither process restarted.

    uv run --project tests pytest tests/e2e/test_e2e_owner_api.py -q -rs

The agent's calls carry OWNER_TOOLS_TOKEN and the owner's carry OWNER_INBOX_TOKEN. Every
change is submitted with REASON, so what a run (or a run that died) left behind can be found
and removed: the seeded graph is the same before and after each test.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx
import psycopg
import pytest
from cac_common.graph import publish, reindex_node
from cac_common.settings import Settings
from e2e_support import ask, components
from psycopg.types.json import Jsonb

pytestmark = pytest.mark.e2e

REASON = "e2e owner api: visitors asked about this"
NO_ROUTE = {"detail": "Not Found"}  # FastAPI's answer for a path that has no route

GIFT_QUESTION = "do you sell gift cards?"
GIFT_TERMS = "Valid for 12 months. Redeemable in the bar."
GIFT_LABEL = {"may_be_public": True, "public_props": ["amounts", "terms"],
              "description": "Gift cards the bar sells"}
GIFT_NODES = {
    "gc_e2e_api_25": {"label": "GiftCard", "name": "$25 gift card",
                      "props": {"amounts": "$25", "terms": GIFT_TERMS, "margin_note": "e2e"}},
    "gc_e2e_api_50": {"label": "GiftCard", "name": "$50 gift card",
                      "props": {"amounts": "$50", "terms": GIFT_TERMS, "margin_note": "e2e"}},
}
# The fake model picks a form whose id words ("gift", "card") are all in the question.
FORM_ID = "ui_form_gift_card"
GIFT_FORM = {
    "component": "GiftCardForm", "primitive": "FormCard",
    "use_when": "Visitor wants to buy or request a gift card.",
    "binds": {"labels": ["Service"], "min": 0, "max": 1},
    "rail_label": "Request a gift card", "chips": ["See the menu"],
    "submit_label": "Send request",
    "fields": [
        {"name": "name", "type": "text", "label": "Your name", "required": True},
        {"name": "contact", "type": "text", "label": "Email or phone", "required": True},
        {"name": "amount", "type": "select", "label": "Amount", "required": True,
         "options": ["$25", "$50"]}],
}

VEGAN_DISH = "mi_chips_and_chunky_guacamole"  # nothing is tagged vegan in the seed
VEGAN_EDGE = {"src": VEGAN_DISH, "dst": "diet_vegan", "type": "SUITABLE_FOR"}
VEGAN_TARGET = f"{VEGAN_DISH}|SUITABLE_FOR|diet_vegan"

EDIT_DISH = "mi_pretzel_bites"
EDIT_QUESTION = "tell me about the pretzel bites"
EDIT_TEXT = "Warm pretzel bites with cheese and beer mustard (e2e owner api)"

KIDS_QUESTION = "do you have a kids menu?"
KIDS_ANSWER = "Yes. Kids eat for $6.95 until 8pm, every day (e2e owner api)."

CREATED_NODES = [*GIFT_NODES, FORM_ID]
COMMIT_TRIALS = 30
OPEN_TRANSACTIONS = ("SELECT count(*) FROM pg_stat_activity WHERE usename = current_user"
                     " AND pid <> pg_backend_pid() AND state <> 'idle'")


def settle(conn: psycopg.Connection, seconds: float = 2.0) -> None:
    """Wait until no other cac_owner transaction is open. je's API answers before its
    transaction commits (test_a_write_is_committed_when_the_api_answers), so the next
    request, a read as cac_owner, or the cleanup could otherwise run ahead of the write."""
    deadline = time.monotonic() + seconds
    while conn.execute(OPEN_TRANSACTIONS).fetchone()[0] and time.monotonic() < deadline:
        time.sleep(0.005)


class Owner:
    """je's API as its two callers: the agent (tools token) and the owner (inbox token).
    Every write waits for the API's transaction to commit unless `wait` is false."""

    def __init__(self, client: httpx.Client, settings: Settings,
                 conn: psycopg.Connection) -> None:
        self._client = client
        self._conn = conn
        self._agent = {"Authorization": f"Bearer {settings.owner_tools_token}"}
        self._owner = {"Authorization": f"Bearer {settings.owner_inbox_token}"}

    def _post(self, path: str, headers: dict, body: dict | None, wait: bool) -> httpx.Response:
        response = self._client.post(path, headers=headers, json=body)
        if wait:
            settle(self._conn)
        return response

    def change(self, action: str, target: str, after: dict, wait: bool = True) -> httpx.Response:
        """POST /owner/changes as the agent."""
        body = {"action": action, "target": target, "after": after, "reason": REASON,
                "evidence": {"topic": "e2e", "count": 12}}
        return self._post("/owner/changes", self._agent, body, wait)

    def agent_get(self, path: str, **params: str) -> httpx.Response:
        return self._client.get(path, headers=self._agent, params=params)

    def agent_post(self, path: str, body: dict | None = None) -> httpx.Response:
        return self._post(path, self._agent, body, wait=True)

    def owner_get(self, path: str) -> httpx.Response:
        return self._client.get(path, headers=self._owner)

    def owner_post(self, path: str, body: dict | None = None) -> httpx.Response:
        return self._post(path, self._owner, body, wait=True)


@pytest.fixture(scope="module")
def owner_api(settings: Settings) -> Iterator[httpx.Client]:
    """Replaces conftest's `owner_api` for this module. je's /healthz answers
    `{"ok": true, "service": "owner", "db": "ok"}`: it has no `status` key, so conftest's
    check would skip every test here although the API is up."""
    try:
        alive = httpx.get(f"{settings.owner_base_url}/healthz", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        alive = False
    if not alive:
        pytest.skip(f"the Owner tools API is not running at {settings.owner_base_url}")
    with httpx.Client(base_url=settings.owner_base_url, timeout=60.0) as client:
        yield client


@pytest.fixture()
def owner(owner_api: httpx.Client, settings: Settings, owner_db: psycopg.Connection) -> Owner:
    if settings.autonomy != "balanced":
        pytest.skip("these loops are the `balanced` column of the SCHEMA 8.6 tier table")
    return Owner(owner_api, settings, owner_db)


def _restore_edits(conn: psycopg.Connection) -> None:
    """Put `before` back for edits of this file that were applied and never reverted."""
    rows = conn.execute(
        "SELECT target, before FROM kg.change WHERE reason = %s AND action = 'update_node'"
        " AND state = 'applied' AND before IS NOT NULL ORDER BY id DESC", (REASON,)).fetchall()
    for target, before in rows:
        conn.execute(
            "UPDATE kg.node SET name = %s, props = %s, visibility = %s, status = %s"
            " WHERE id = %s",
            (before["name"], Jsonb(before["props"]), before["visibility"], before["status"],
             target))
        reindex_node(conn, target)


def _clean(conn: psycopg.Connection, business_id: str, extra_nodes: list[str]) -> None:
    """Remove everything this file writes through the API, then publish the seeded graph."""
    settle(conn)
    _restore_edits(conn)
    conn.execute("DELETE FROM kg.node WHERE id = ANY(%s)", ([*CREATED_NODES, *extra_nodes],))
    conn.execute("DELETE FROM kg.node WHERE label = 'FAQ' AND props ->> 'answer' = %s",
                 (KIDS_ANSWER,))
    conn.execute("DELETE FROM kg.edge WHERE src = %s AND dst = %s AND type = %s",
                 (VEGAN_EDGE["src"], VEGAN_EDGE["dst"], VEGAN_EDGE["type"]))
    conn.execute("DELETE FROM kg.label WHERE label = 'GiftCard'")
    conn.execute("DELETE FROM kg.change WHERE reason = %s", (REASON,))
    publish(conn, business_id)


@pytest.fixture(autouse=True)
def created(serve: httpx.Client, owner_api: httpx.Client, owner_db: psycopg.Connection,
            settings: Settings) -> Iterator[list[str]]:
    """Clean before (an earlier run may have died) and after. A test appends the ids of
    nodes the API named for it (a gap), so they are removed too."""
    extra: list[str] = []
    _clean(owner_db, settings.business_id, extra)
    try:
        yield extra
    finally:
        _clean(owner_db, settings.business_id, extra)


def pending(response: httpx.Response) -> int:
    """The change waits for the owner (tier one_tap). Returns its id."""
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["tier"], body["state"]) == ("one_tap", "pending")
    return body["change_id"]


def decided(response: httpx.Response, state: str) -> int:
    """An approve or revert went through and published by itself. Returns the new version."""
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == state
    return body["graph_version"]


def approve(owner: Owner, change_id: int) -> int:
    return decided(owner.owner_post(f"/owner/changes/{change_id}/approve"), "applied")


def submit_gift_cards(owner: Owner) -> list[int]:
    """The agent's three changes for a new node type: the label first, then two nodes."""
    label = pending(owner.change("create_label", "GiftCard", GIFT_LABEL))
    nodes = [pending(owner.change("create_node", node_id, after))
             for node_id, after in GIFT_NODES.items()]
    return [label, *nodes]


def menu_item(surface: dict, item_id: str) -> dict | None:
    """The item in the surface's first view, when that view is a MenuList holding it."""
    first = surface["views"][0]
    if surface["kind"] != "answer" or first["component"] != "MenuList":
        return None
    return next((item for item in first["data"]["items"] if item["id"] == item_id), None)


def wp5(response: httpx.Response, endpoint: str) -> list | dict:
    """The JSON of a wp5 endpoint; skips when je's branch has no such route yet."""
    if response.status_code == 404 and response.json() == NO_ROUTE:
        pytest.skip(f"je wp5 not available: {endpoint}")
    assert response.status_code == 200, (endpoint, response.status_code, response.text)
    return response.json()


def test_agent_adds_a_node_type(serve, owner, session_id):
    """Section 10 "Agent adds a node type": create_label GiftCard plus two create_node are
    pending; once the owner approves each, the question returns a ListCard of both."""
    change_ids = submit_gift_cards(owner)
    waiting = ask(serve, GIFT_QUESTION, session_id)
    assert "ListCard" not in components(waiting)  # drafts never reach the public copy

    versions = [approve(owner, change_id) for change_id in change_ids]

    response = serve.post("/v1/intent", json={"text": GIFT_QUESTION, "session_id": session_id})
    surface = response.json()
    assert surface["kind"] == "answer"
    assert surface["meta"]["graph_version"] == versions[-1]  # approving published it
    first = surface["views"][0]
    assert first["component"] == "ListCard"
    assert [item["id"] for item in first["data"]["items"]] == list(GIFT_NODES)
    facts = {fact["name"]: fact["value"] for fact in first["data"]["items"][0]["facts"]}
    assert facts == {"Amounts": "$25", "Terms": GIFT_TERMS}
    assert "margin_note" not in response.text  # a prop outside public_props stays private


def test_agent_adds_an_element(serve, owner, owner_db, session_id):
    """Section 10 "Agent adds an element": a create_component FormCard is pending; after
    approval the same question also returns the form, and a submit stores a `form` lead."""
    for change_id in submit_gift_cards(owner):
        approve(owner, change_id)
    form_change = pending(owner.change("create_component", FORM_ID, GIFT_FORM))
    assert components(ask(serve, GIFT_QUESTION, session_id))[0] == "ListCard"
    shown = ask(serve, GIFT_QUESTION, session_id)  # a model may add another approved form
    assert all(view["data"].get("form") != FORM_ID for view in shown["views"])

    version = approve(owner, form_change)

    surface = ask(serve, GIFT_QUESTION, session_id)
    assert surface["meta"]["graph_version"] == version
    assert components(surface)[:2] == ["ListCard", "FormCard"]
    card = surface["views"][1]["data"]
    assert (card["form"], card["title"], card["submit_label"]) == (
        FORM_ID, "Request a gift card", "Send request")
    assert [field["name"] for field in card["fields"]] == ["name", "contact", "amount"]

    submit = serve.post("/v1/action", json={
        "name": "submit_form", "session_id": session_id, "component": FORM_ID,
        "payload": {"form": FORM_ID,
                    "values": {"name": "E2E Guest", "contact": "e2e@example.invalid",
                               "amount": "$50"}}})
    assert submit.status_code == 200
    lead = owner_db.execute(
        "SELECT kind, component, payload -> 'values' ->> 'amount' FROM ops.lead"
        " WHERE id = %s", (submit.json()["lead_id"],)).fetchone()
    assert lead == ("form", FORM_ID, "$50")


def test_agent_tags_a_dish(serve, owner, session_id):
    """Section 10 "Agent tags a dish": a SUITABLE_FOR edge to Vegan is applied and published
    at once in balanced mode and renders unverified; after /owner/verify it is a badge."""
    assert menu_item(ask(serve, "vegan options", session_id), VEGAN_DISH) is None

    tagged = owner.change("create_edge", VEGAN_TARGET, VEGAN_EDGE)
    assert tagged.status_code == 200, tagged.text
    body = tagged.json()
    assert (body["tier"], body["state"]) == ("auto", "applied")

    surface = ask(serve, "vegan options", session_id)
    assert surface["meta"]["graph_version"] == body["graph_version"]  # tier auto publishes
    item = menu_item(surface, VEGAN_DISH)
    assert item is not None
    assert item["badges"] == [{"diet": "Vegan", "verified": False}]
    assert "not verified, ask staff" in surface["views"][0]["text"].lower()

    inbox = owner.owner_get("/owner/inbox.json")
    assert inbox.status_code == 200
    edge_ids = [tag["edge_id"] for tag in inbox.json()["unverified_tags"]
                if (tag["src"], tag["dst"], tag["type"]) == tuple(VEGAN_EDGE.values())]
    assert len(edge_ids) == 1
    verified = owner.owner_post("/owner/verify", {"edge_ids": edge_ids})
    assert verified.status_code == 200, verified.text

    surface = ask(serve, "vegan options", session_id)
    assert surface["meta"]["graph_version"] == verified.json()["graph_version"]
    assert menu_item(surface, VEGAN_DISH)["badges"] == [{"diet": "Vegan", "verified": True}]


def test_agent_edits_a_dish(serve, owner, session_id):
    """Section 10 "Agent edits a dish": update_node on a description is pending until the
    owner approves; then the Serve API shows the new text; after revert the old one."""
    old_text = menu_item(ask(serve, EDIT_QUESTION, session_id), EDIT_DISH)["description"]
    assert old_text and old_text != EDIT_TEXT

    change_id = pending(owner.change("update_node", EDIT_DISH,
                                     {"props": {"description": EDIT_TEXT}}))
    assert menu_item(ask(serve, EDIT_QUESTION, session_id), EDIT_DISH)["description"] == old_text

    version = approve(owner, change_id)
    edited = ask(serve, EDIT_QUESTION, session_id)
    assert edited["meta"]["graph_version"] == version
    assert menu_item(edited, EDIT_DISH)["description"] == EDIT_TEXT

    version = decided(owner.owner_post(f"/owner/changes/{change_id}/revert"), "reverted")
    reverted = ask(serve, EDIT_QUESTION, session_id)
    assert reverted["meta"]["graph_version"] == version
    assert menu_item(reverted, EDIT_DISH)["description"] == old_text


def test_agent_tries_the_locked_tier(serve, owner, owner_db, session_id):
    """Section 10 "Agent tries the locked tier": setting verified_by_owner, reading a
    Customer, and approving or verifying with the agent's token are each refused."""
    refused = owner.change("create_edge", VEGAN_TARGET, {**VEGAN_EDGE, "verified_by_owner": True})
    assert refused.status_code == 403
    assert (refused.json()["tier"], refused.json()["state"]) == ("locked", "rejected")
    assert menu_item(ask(serve, "vegan options", session_id), VEGAN_DISH) is None

    customer = owner_db.execute(
        "SELECT name FROM kg.node WHERE label = 'Customer' ORDER BY id LIMIT 1").fetchone()[0]
    by_label = owner.agent_get("/owner/graph/search", label="Customer")
    assert by_label.status_code == 403
    assert by_label.json()["detail"]["tier"] == "locked"
    by_name = owner.agent_get("/owner/graph/search", q=customer)
    assert by_name.status_code == 200
    assert by_name.json()["nodes"] == []
    assert customer not in by_name.text

    change_id = pending(owner.change("update_node", EDIT_DISH,
                                     {"props": {"description": EDIT_TEXT}}))
    for path, body in ((f"/owner/changes/{change_id}/approve", None),
                       ("/owner/verify", {"node_ids": [EDIT_DISH]})):
        attempt = owner.agent_post(path, body)
        assert attempt.status_code == 403
        assert attempt.json()["detail"]["tier"] == "locked"
    state, verified = owner_db.execute(
        "SELECT c.state, n.verified_by_owner FROM kg.change c JOIN kg.node n ON n.id = c.target"
        " WHERE c.id = %s", (change_id,)).fetchone()
    assert (state, verified) == ("pending", False)
    assert menu_item(ask(serve, EDIT_QUESTION, session_id), EDIT_DISH)["description"] != EDIT_TEXT


@pytest.mark.xfail(strict=True, reason=(
    "je: app/infra/db.py get_conn commits when the dependency exits, and FastAPI (0.118 and"
    " later) runs that exit after the response is sent, so POST /owner/changes, approve,"
    " revert and verify answer before their write and publish are committed. Commit before"
    " answering (conn.commit() in the route, or Depends(get_conn, scope='function'))."))
def test_a_write_is_committed_when_the_api_answers(owner, owner_db):
    """SCHEMA 8.6: a change "returns { change_id, tier, state }" for a record that exists,
    and tier auto is "applied and published immediately". The caller's next request (the
    agent's create_node after create_label, a visitor's question, wp5's pre-warm) must see
    it. Probed with refused changes, which write one kg.change row and nothing else."""
    unseen = 0
    for _ in range(COMMIT_TRIALS):
        refused = owner.change("create_edge", VEGAN_TARGET,
                               {**VEGAN_EDGE, "verified_by_owner": True}, wait=False)
        row = owner_db.execute("SELECT 1 FROM kg.change WHERE id = %s",
                               (refused.json()["change_id"],)).fetchone()
        unseen += row is None
        settle(owner_db)
    assert unseen == 0, f"{unseen} of {COMMIT_TRIALS} answers came before the commit"


def _open_gap(owner: Owner, topic: str) -> dict:
    """The open gap for `topic`, after /owner/topics folded the new log rows in."""
    topics = wp5(owner.agent_get("/owner/topics"), "GET /owner/topics")
    assert any(row["topic"] == topic and row["kind"] == "gap" for row in topics)
    gaps = wp5(owner.agent_get("/owner/gaps", state="open"), "GET /owner/gaps")
    matching = [gap for gap in gaps if gap["topic"] == topic]
    assert len(matching) == 1
    return matching[0]


@pytest.fixture()
def gap_sessions(session_id: str, settings: Settings) -> list[str]:
    """As many visitor sessions as a gap needs before the owner is asked about it."""
    extra = range(1, settings.gap_ask_min_sessions)
    return [session_id, *(f"{session_id}-{n}" for n in extra)]


def test_gap_loop(serve, owner, owner_db, gap_sessions, created):
    """Section 10 "Gap loop": an unknown question logs a gap; after the owner's answer goes
    in through POST /owner/answers and a publish, the same question returns Answer with
    verified true. Written against SCHEMA 8.6; needs je's wp5."""
    session_id = gap_sessions[0]
    for session in gap_sessions:
        assert ask(serve, KIDS_QUESTION, session)["kind"] == "gap"
    topic = owner_db.execute(
        "SELECT gap_topic FROM ops.intent_log WHERE session_id = %s ORDER BY id DESC LIMIT 1",
        (session_id,)).fetchone()[0]
    assert topic

    gap = _open_gap(owner, topic)
    created.append(gap["gap_id"])
    assert gap["count"] >= 1
    wp5(owner.agent_post(f"/owner/gaps/{gap['gap_id']}/asked"), "POST /owner/gaps/{id}/asked")
    wp5(owner.agent_post("/owner/answers", {"gap_id": gap["gap_id"],
                                            "answer_text": KIDS_ANSWER}), "POST /owner/answers")
    wp5(owner.agent_post("/owner/publish"), "POST /owner/publish")

    surface = ask(serve, KIDS_QUESTION, session_id)
    assert surface["kind"] == "answer"
    answer = surface["views"][0]
    assert answer["component"] == "Answer"
    assert answer["data"]["answer"] == KIDS_ANSWER
    assert answer["data"]["verified"] is True
