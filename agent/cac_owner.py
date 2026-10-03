#!/usr/bin/env python3
"""Owner tools client for the CAC agent (stdlib only, so it runs inside the sandbox).

Every command prints one JSON document. It reads topics and counts only; it never touches
raw visitor text. Env: OWNER_BASE_URL (default http://127.0.0.1:8081), OWNER_TOOLS_TOKEN.
SCHEMA section 8.6 is the contract.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PLANS = Path(__file__).resolve().parent / "plans"
ASK_TEMPLATE = ("{count} visitors asked about {topic}. I have nothing confirmed. "
                "What should I tell them?")


def load_agent_env() -> None:
    """Inside the sandbox the agent's shell has no CAC env; box/agent_install.sh writes
    agent.env (git-ignored) next to this file. Real env vars win."""
    f = Path(__file__).resolve().parent / "agent.env"
    if f.exists():
        for line in f.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() and not k.startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())


class OwnerApi:
    def __init__(self, base: str | None = None, token: str | None = None):
        self.base = (base or os.environ.get("OWNER_BASE_URL", "http://127.0.0.1:8081")).rstrip("/")
        self.token = token or os.environ.get("OWNER_TOOLS_TOKEN", "")

    def call(self, method: str, path: str, body: dict | None = None) -> dict | list:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or "null")
        except urllib.error.HTTPError as e:
            return {"error": e.code, "detail": e.read().decode()[:300]}


def planned_topics() -> set[str]:
    """Topics a plan in plans/ answers with a graph change rather than a question."""
    return {t.lower() for f in PLANS.glob("*.json")
            for t in json.loads(f.read_text()).get("topics", [])}


def ask_top_gap(api: OwnerApi) -> dict:
    """Move 1: put the most-asked open gap to the owner. Returns the message to send.
    Gaps that a plan covers (a missing type, not a missing fact) are left to move 2."""
    gaps = api.call("GET", "/owner/gaps?state=open")
    if isinstance(gaps, list):
        gaps = [g for g in gaps if g["topic"].lower() not in planned_topics()]
    if not isinstance(gaps, list) or not gaps:
        return {"asked": False, "reason": "no open gaps"}
    top = max(gaps, key=lambda g: g["count"])
    res = api.call("POST", f"/owner/gaps/{top['gap_id']}/asked")
    if isinstance(res, dict) and "error" in res:
        return {"asked": False, "reason": res}
    return {"asked": True, "gap_id": top["gap_id"],
            "message": ASK_TEMPLATE.format(count=top["count"], topic=top["topic"])}


def record_answer(api: OwnerApi, gap_id: str, text: str) -> dict:
    """The owner's reply, verbatim, then publish."""
    ans = api.call("POST", "/owner/answers", {"gap_id": gap_id, "answer_text": text})
    if isinstance(ans, dict) and "error" in ans:
        return {"answered": False, "reason": ans}
    return {"answered": True, "published": api.call("POST", "/owner/publish")}


def propose_plan(api: OwnerApi, plan_path: str, topic: str) -> dict:
    """Move 2: post a plan's changes with a reason and evidence taken from the topic count."""
    topics = api.call("GET", "/owner/topics")
    hit = next((t for t in topics if t["topic"].lower() == topic.lower()), None) \
        if isinstance(topics, list) else None
    if hit is None:
        return {"proposed": [], "reason": f"no topic '{topic}'"}
    plan = json.loads(Path(plan_path).read_text())
    evidence = f"{hit['count']} visitors in {hit['sessions']} sessions asked about {topic}"
    out = []
    for ch in plan["changes"]:
        res = api.call("POST", "/owner/changes", {
            "action": ch["action"], "target": ch["target"], "after": ch["after"],
            "reason": plan["reason"].format(topic=topic), "evidence": evidence})
        out.append({"action": ch["action"], **(res if isinstance(res, dict) else {})})
    return {"proposed": out}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cac_owner")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("digest", "topics", "gaps", "schema", "ask-top-gap", "publish"):
        sub.add_parser(name)
    s = sub.add_parser("changes")
    s.add_argument("--state", default="")
    s = sub.add_parser("answer")
    s.add_argument("gap_id")
    s.add_argument("text")
    s = sub.add_parser("special-hours")
    s.add_argument("date")
    s.add_argument("--closed", action="store_true")
    for opt in ("--opens", "--closes", "--note"):
        s.add_argument(opt)
    s = sub.add_parser("propose")
    s.add_argument("plan")
    s.add_argument("--topic", required=True)
    s = sub.add_parser("change")
    s.add_argument("action")
    for opt in ("--target", "--after", "--reason", "--evidence"):
        s.add_argument(opt, required=True)
    return p


def special_hours(api: OwnerApi, a: argparse.Namespace) -> dict:
    fields = {"date": a.date, "closed": a.closed, "opens": a.opens, "closes": a.closes,
              "note": a.note}
    body = {k: v for k, v in fields.items() if v is not None}
    res = api.call("POST", "/owner/special-hours", body)
    if "error" not in res:
        api.call("POST", "/owner/publish")
    return res


def post_change(api: OwnerApi, a: argparse.Namespace) -> dict:
    return api.call("POST", "/owner/changes", {
        "action": a.action, "target": json.loads(a.target), "after": json.loads(a.after),
        "reason": a.reason, "evidence": a.evidence})


def main(argv: list[str]) -> int:
    a = build_parser().parse_args(argv)
    load_agent_env()
    api = OwnerApi()
    handlers = {
        "ask-top-gap": lambda: ask_top_gap(api),
        "answer": lambda: record_answer(api, a.gap_id, a.text),
        "special-hours": lambda: special_hours(api, a),
        "publish": lambda: api.call("POST", "/owner/publish"),
        "propose": lambda: propose_plan(api, a.plan, a.topic),
        "change": lambda: post_change(api, a),
        "changes": lambda: api.call("GET", "/owner/changes?state=" + a.state),
        "gaps": lambda: api.call("GET", "/owner/gaps?state=open"),
    }
    handler = handlers.get(a.cmd, lambda: api.call("GET", f"/owner/{a.cmd}"))
    print(json.dumps(handler()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
