"""Mock of SCHEMA 8.6 for developing the agent before je's API lands. Delete when it does.
Run: python3 agent/dev/mock_owner_api.py [port]   Token: OWNER_TOOLS_TOKEN (default dev-agent-token)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("OWNER_TOOLS_TOKEN", "dev-agent-token")
STATE = {
    "gaps": {
        "gap_1": {"gap_id": "gap_1", "topic": "parking", "count": 7, "state": "open"},
        "gap_2": {"gap_id": "gap_2", "topic": "dog patio", "count": 3, "state": "open"}},
    "topics": [{"topic": "gift cards", "count": 12, "sessions": 9, "kind": "unmatched",
                "component": "Answer"}],
    "changes": [], "faqs": [], "published": 0,
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def route(self, method):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self.send(401, {"detail": "bad token"})
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else {}
        path, _, q = self.path.partition("?")
        if method == "GET" and path == "/owner/gaps":
            return self.send(200, [g for g in STATE["gaps"].values() if g["state"] == "open"])
        if method == "GET" and path == "/owner/topics":
            return self.send(200, STATE["topics"])
        if method == "GET" and path == "/owner/changes":
            return self.send(200, STATE["changes"])
        if method == "GET" and path == "/owner/digest":
            return self.send(200, {"questions_today": 30, "top_topics": STATE["topics"],
                                   "open_gaps": 2, "pending_changes": len(STATE["changes"]),
                                   "new_leads": []})
        if method == "POST" and path.startswith("/owner/gaps/") and path.endswith("/asked"):
            gid = path.split("/")[3]
            if any(g["state"] == "asked" for g in STATE["gaps"].values()):
                return self.send(409, {"detail": "another gap is asked"})
            STATE["gaps"][gid]["state"] = "asked"
            return self.send(200, {"gap_id": gid, "state": "asked"})
        if method == "POST" and path == "/owner/answers":
            g = STATE["gaps"].get(body.get("gap_id"))
            if not g or g["state"] != "asked":
                return self.send(409, {"detail": "gap not in state asked"})
            g["state"] = "answered"; STATE["faqs"].append(body["answer_text"])
            return self.send(200, {"faq": "faq_1", "verified": True})
        if method == "POST" and path == "/owner/publish":
            STATE["published"] += 1
            return self.send(200, {"graph_version": 1 + STATE["published"]})
        if method == "POST" and path == "/owner/special-hours":
            return self.send(200, {"node_id": "sh_1"})
        if method == "POST" and path == "/owner/changes":
            cid = f"chg_{len(STATE['changes']) + 1}"
            STATE["changes"].append(
                {"change_id": cid, "tier": "one_tap", "state": "pending", **body})
            return self.send(200, {"change_id": cid, "tier": "one_tap", "state": "pending"})
        if method == "GET" and path == "/_state":
            return self.send(200, STATE)
        return self.send(404, {"detail": "not found"})

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
