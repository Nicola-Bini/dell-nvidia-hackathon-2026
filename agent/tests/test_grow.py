"""Move 3 (grow) against a fake Owner tools API: no network, no model.

The graph below is a bike shop on purpose: nothing in the agent may depend on one business.
Run: python3 -m unittest agent.tests.test_grow -v   (or discover -s agent/tests -p test_grow.py)
"""
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import cac_grow  # noqa: E402
import cac_owner  # noqa: E402


def node(node_id, label, name, **props):
    return {"id": node_id, "label": label, "name": name, "props": props, "status": "approved"}


class FakeApi:
    """Answers the read endpoints from memory and records every write."""

    def __init__(self):
        bikes = [node(f"bk_{i:02d}", "Bike", f"Bike {i}", description=f"model {i}")
                 for i in range(60)]
        uses = [node("use_commute", "Use", "Commuting"), node("use_trail", "Use", "Trail")]
        self.nodes = bikes + uses + [node("biz_shop", "Business", "Spoke & Chain")]
        self.edges = [{"id": 1, "src": "bk_00", "dst": "use_trail", "type": "GOOD_FOR",
                       "status": "approved"}]
        self.topics = [
            {"topic": "repair booking", "count": 9, "sessions": 7, "kind": "gap",
             "state": "open"},
            {"topic": "opening time", "count": 4, "sessions": 4, "kind": "gap", "state": "open"},
            {"topic": "ListCard", "count": 30, "sessions": 20, "kind": "answer"}]
        self.changes = []
        self.posts = []
        self.searches = 0

    def call(self, method, path, body=None):
        url = urlparse(path)
        if method == "POST" and url.path == "/owner/changes":
            return self._post(body)
        if method == "POST" and url.path.endswith("/asked"):
            return {"state": "asked"}
        return getattr(self, "_" + url.path.rsplit("/", 1)[-1])(parse_qs(url.query))

    def _post(self, body):
        self.posts.append(body)
        if body["action"] == "create_edge" and body["target"].startswith("bk_00|GOOD_FOR|use_tr"):
            return {"error": 409, "detail": "that edge already exists"}
        state = "applied" if body["action"] == "create_edge" else "pending"
        return {"change_id": len(self.posts), "tier": "auto", "state": state}

    def _schema(self, _):
        return {"labels": [{"label": "Bike", "public_props": ["description"], "status": "approved"},
                           {"label": "Use", "public_props": [], "status": "approved"},
                           {"label": "Business", "public_props": [], "status": "approved"},
                           {"label": "Customer", "locked": True}],
                "edge_types": [{"type": "GOOD_FOR", "description": "what a thing suits"}],
                "catalog": [{"id": "ui_bike_list", "name": "BikeList", "props": {
                    "component": "BikeList", "use_when": "bikes", "primitive": "ListCard",
                    "binds": {"labels": ["Bike"]}}}]}

    def _search(self, query):
        self.searches += 1
        label, q = query["label"][0], query.get("q", [""])[0]
        hits = sorted((n for n in self.nodes if n["label"] == label and q in n["id"]),
                      key=lambda n: n["id"])[:cac_grow.PAGE]
        ids = {n["id"] for n in hits}
        return {"nodes": hits,
                "edges": [e for e in self.edges if e["src"] in ids or e["dst"] in ids]}

    def _topics(self, _):
        return self.topics

    def _changes(self, _):
        return self.changes

    def _gaps(self, _):
        return [{"gap_id": "gap_" + t["topic"].replace(" ", "_"), "topic": t["topic"],
                 "count": t["count"]} for t in self.topics if t["kind"] == "gap"]


class GrowTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cac_grow.STATE = Path(tmp.name) / "grow_state.json"
        self.api = FakeApi()

    def task(self, name):
        """Run heartbeats until the rotation reaches the named task."""
        for _ in range(len(cac_grow.ROTATION)):
            packet = cac_grow.next_task(self.api)
            if packet["task"] == name:
                return packet
        self.fail(f"rotation never offered {name}")

    def test_nodes_of_reads_past_the_25_node_page(self):
        nodes, edges = cac_grow.nodes_of(self.api, "Bike")
        self.assertEqual(len(nodes), 60)
        self.assertEqual(len(edges), 1)

    def test_classify_walks_a_label_in_batches_with_tags_and_links(self):
        first = cac_grow.next_task(self.api)
        self.assertEqual((first["task"], first["label"]), ("classify", "Bike"))
        self.assertEqual([n["id"] for n in first["nodes"]][:2], ["bk_00", "bk_01"])
        self.assertEqual(first["nodes"][0]["links"], ["GOOD_FOR -> use_trail"])
        self.assertEqual(sorted(t["id"] for t in first["tags"]["Use"]),
                         ["use_commute", "use_trail"])
        self.assertEqual(first["edge_types"][0]["seen"], ["Bike -> Use"])
        self.assertNotIn("Customer", first["tags"])
        second = self.task("classify")
        self.assertEqual(second["nodes"][0]["id"], f"bk_{cac_grow.BATCH:02d}")

    def test_topics_offers_the_top_uncovered_topic_once(self):
        packet = self.task("topics")
        self.assertEqual(packet["topic"], "repair booking")
        self.assertIn("9 visitors", packet["why"])
        self.assertEqual([e["component"] for e in packet["elements"]], ["BikeList"])
        self.assertEqual(self.task("topics")["topic"], "opening time")

    def test_invent_lists_types_no_element_shows_and_past_proposals(self):
        self.api.changes = [{"action": "create_component", "target": "ui_faq_list",
                             "state": "rejected", "evidence": {}}]
        packet = self.task("invent")
        self.assertEqual(packet["about"][0]["name"], "Spoke & Chain")
        self.assertIn("Use", packet["unshown"])
        self.assertNotIn("Bike", packet["unshown"])
        self.assertEqual(packet["already"], ["create_component ui_faq_list (rejected)"])

    def test_a_full_inbox_holds_back_everything_but_classify(self):
        self.api.changes = [{"action": "create_node", "target": f"x_{i}", "state": "pending",
                             "evidence": {}} for i in range(cac_grow.MAX_PENDING + 1)]
        tasks = {cac_grow.next_task(self.api)["task"] for _ in cac_grow.ROTATION}
        self.assertEqual(tasks, {"classify"})

    def test_apply_orders_dedupes_and_carries_the_evidence(self):
        self.task("topics")
        self.api.changes = [{"action": "create_label", "target": "Tool", "state": "rejected",
                             "evidence": {}}]
        res = cac_grow.apply_changes(self.api, [
            {"action": "create_edge", "target": "bk_01|GOOD_FOR|use_commute", "reason": "r"},
            {"action": "create_edge", "target": {"src": "bk_00", "type": "GOOD_FOR",
                                                 "dst": "use_trail"}, "reason": "r"},
            {"action": "create_node", "target": "rep_tune", "reason": "r",
             "after": {"label": "Repair", "name": "Tune-up"}},
            {"action": "create_label", "target": "Repair", "reason": "r",
             "after": {"public_props": ["details"], "may_be_public": True}},
            {"action": "create_label", "target": "Tool", "reason": "r"},
            {"action": "drop_table", "target": "x", "reason": "r"}])
        self.assertEqual([p["action"] for p in self.api.posts],
                         ["create_label", "create_node", "create_edge", "create_edge"])
        self.assertEqual(self.api.posts[0]["evidence"], {
            "text": "9 visitors in 7 sessions asked about repair booking",
            "task": "topics", "topic": "repair booking"})
        self.assertEqual((res["applied"], res["pending"], res["skipped"]), (1, 2, 2))
        self.assertEqual(len(res["refused"]), 1)
        self.assertIn("1 live", res["summary"])
        self.assertIn("2 waiting", res["summary"])

    def test_apply_reads_a_list_wrapped_in_prose_or_a_code_fence(self):
        text = 'Here you go:\n```json\n[{"action": "create_edge", "target": "a|T|b"}]\n```'
        self.assertEqual(cac_grow.parse_changes(text)[0]["target"], "a|T|b")
        self.assertEqual(cac_grow.parse_changes("no list"), None)

    def test_apply_reads_the_changes_file_once(self):
        self.task("classify")
        path = cac_grow.STATE.parent / "changes.json"
        path.write_text('[{"action": "create_edge", "target": "bk_01|GOOD_FOR|use_trail"}]')
        res = cac_owner.apply_source(self.api, str(path))
        self.assertEqual(res["applied"], 1)
        self.assertEqual(self.api.posts[0]["evidence"]["task"], "classify")
        self.assertFalse(path.exists())
        self.assertIn("error", cac_owner.apply_source(self.api, "not json"))

    def test_ask_top_gap_leaves_a_topic_the_agent_already_built_for(self):
        self.api.changes = [{"action": "create_label", "target": "Repair", "state": "pending",
                             "evidence": {"topic": "repair booking"}}]
        asked = cac_owner.ask_top_gap(self.api)
        self.assertEqual(asked["gap_id"], "gap_opening_time")

    def test_nothing_in_the_grow_move_names_one_business(self):
        grow = (AGENT / "cac_grow.py").read_text()
        prompt = (AGENT / "HEARTBEAT.md").read_text().split("## grow")[1]
        for word in ("MenuItem", "Kenmore", "gift", "Diet", "Allergen", "restaurant"):
            self.assertNotIn(word, grow)
            self.assertNotIn(word, prompt)


if __name__ == "__main__":
    unittest.main()
