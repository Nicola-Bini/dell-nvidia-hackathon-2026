"""wp4 proof: a seeded gap is asked and, after a reply, answered and published; a seeded
gift-card topic yields a pending create_label, two create_node and one create_component.
Runs against the mock. Run: python3 -m unittest discover -s agent/tests
"""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT / "dev"))
import mock_owner_api as mock  # noqa: E402


def cli(env, *args):
    out = subprocess.run([sys.executable, str(AGENT / "cac_owner.py"), *args], env=env,
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


class Wp4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), mock.H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env = {**os.environ, "OWNER_TOOLS_TOKEN": mock.TOKEN,
                   "OWNER_BASE_URL": f"http://127.0.0.1:{cls.srv.server_port}"}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_gap_loop(self):
        asked = cli(self.env, "ask-top-gap")
        self.assertEqual(asked["gap_id"], "gap_1")
        self.assertIn("7 visitors asked about parking", asked["message"])
        again = cli(self.env, "ask-top-gap")
        self.assertFalse(again["asked"])  # only one gap asked at a time
        res = cli(self.env, "answer", "gap_1", "Free after 6pm on Beacon St.")
        self.assertTrue(res["answered"])
        self.assertIn("graph_version", res["published"])

    def test_gift_card_plan(self):
        res = cli(self.env, "propose", str(AGENT / "plans/gift_card.json"), "--topic", "gift cards")
        actions = [c["action"] for c in res["proposed"]]
        self.assertEqual(sorted(actions), ["create_component", "create_label",
                                           "create_node", "create_node"])
        self.assertTrue(all(c["state"] == "pending" for c in res["proposed"]))
        chg = cli(self.env, "changes", "--state", "pending")
        self.assertIn("12 visitors", chg[0]["evidence"])

    def test_bad_token_refused(self):
        env = {**self.env, "OWNER_TOOLS_TOKEN": "wrong"}
        self.assertEqual(cli(env, "gaps")["error"], 401)


if __name__ == "__main__":
    unittest.main()
