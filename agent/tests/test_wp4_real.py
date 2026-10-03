"""wp4 proof against je's real Owner tools API and the real Serve API.

A seeded gap is asked and, after a reply, answered and published, and the same question then
returns the owner's words, verified; a seeded gift-card topic yields a pending create_label,
two create_node and one create_component. Needs a fresh demo state (box/demo_reset.sh).
Run: set -a; . ./.env; set +a; python3 -m unittest discover -s agent/tests -v
"""
import json
import os
import subprocess
import sys
import unittest
import urllib.request
import uuid
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
SERVE = os.environ.get("SERVE_BASE_URL", "http://127.0.0.1:8082")
REPLY = "Free street parking on Hampshire St after 6pm, and a paid lot on Portland St."


def cli(*args, token=None):
    env = {**os.environ, **({"OWNER_TOOLS_TOKEN": token} if token else {})}
    out = subprocess.run([sys.executable, str(AGENT / "cac_owner.py"), *args], env=env,
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def ask_serve(text):
    body = json.dumps({"text": text, "session_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"{SERVE}/v1/intent", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


class Wp4RealApi(unittest.TestCase):
    def test_1_gap_loop(self):
        asked = cli("ask-top-gap")
        self.assertTrue(asked["asked"], asked)
        self.assertEqual(asked["gap_id"], "gap_parking")  # gift cards is left to move 2
        self.assertIn("visitors asked about parking", asked["message"])
        res = cli("answer", asked["gap_id"], REPLY)
        self.assertTrue(res["answered"], res)
        self.assertIn("graph_version", res["published"])
        surface = json.dumps(ask_serve("is there parking near you?"))
        self.assertIn("Hampshire St", surface)

    def test_2_gift_card_plan(self):
        res = cli("propose", str(AGENT / "plans/gift_card.json"), "--topic", "gift cards")
        got = sorted((c["action"], c.get("state")) for c in res["proposed"])
        self.assertEqual(got, [("create_component", "pending"), ("create_label", "pending"),
                               ("create_node", "pending"), ("create_node", "pending")], res)

    def test_3_bad_token_refused(self):
        self.assertIn(cli("gaps", token="wrong")["error"], (401, 403))


if __name__ == "__main__":
    unittest.main()
