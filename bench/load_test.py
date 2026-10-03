# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "pyyaml"]
# ///
"""Load test of POST /v1/intent at 1, 4 and 8 concurrent, optionally with an agent turn
in flight. Fresh text per request defeats the exact cache, so every call reaches the model
(set --cached to repeat texts instead). Prints a latency table. uv run bench/load_test.py
"""
import argparse
import itertools
import os
import statistics
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("SERVE_BASE_URL", "http://127.0.0.1:8082")
SUFFIXES = ["", " please", " today", " tonight", " right now", " for two", " thanks", " ok"]


def texts(n: int, cached: bool) -> list[str]:
    base = [i["text"] for i in
            yaml.safe_load((ROOT / "demo/kenmore/intents.yaml").read_text())["intents"]]
    if cached:
        return list(itertools.islice(itertools.cycle(base), n))
    nonce = uuid.uuid4().hex[:6]  # per run, so no run hits another run's cache
    return [f"{base[k % len(base)]}{SUFFIXES[(k // len(base)) % len(SUFFIXES)]} {nonce}"
            for k in range(n)]


def one(client: httpx.Client, text: str) -> tuple[float, int, bool]:
    t0 = time.perf_counter()
    try:
        body = {"text": text, "session_id": str(uuid.uuid4())}
        r = client.post(f"{BASE}/v1/intent", json=body, timeout=60)
        code, busy = r.status_code, "busy right now" in r.text
    except httpx.HTTPError:
        code, busy = 0, False
    return time.perf_counter() - t0, code, busy


def agent_turn(cmd: list[str], stop: threading.Event) -> None:
    while not stop.is_set():
        subprocess.run(cmd, capture_output=True, timeout=300)


def run(conc: int, n: int, cached: bool, agent_cmd: list[str] | None) -> dict:
    stop = threading.Event()
    bg = None
    if agent_cmd:
        bg = threading.Thread(target=agent_turn, args=(agent_cmd, stop), daemon=True)
        bg.start()
    with httpx.Client() as client, ThreadPoolExecutor(conc) as pool:
        res = list(pool.map(lambda t: one(client, t), texts(n, cached)))
    stop.set()
    lat = sorted(r[0] for r in res)
    errs = sum(1 for r in res if r[1] != 200)
    busy = sum(1 for r in res if r[2])
    return {"conc": conc, "agent": bool(agent_cmd), "n": n, "p50": statistics.median(lat),
            "p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))], "errors": errs, "busy": busy}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=40)
    ap.add_argument("--cached", action="store_true")
    ap.add_argument("--agent-cmd", help="command that runs one agent turn, looped in background")
    a = ap.parse_args()
    rows = [run(c, a.n, a.cached, None) for c in (1, 4, 8)]
    if a.agent_cmd:
        rows.append(run(4, a.n, a.cached, a.agent_cmd.split()))
    print("| concurrent | agent turn | n | p50 s | p95 s | errors | busy fallbacks |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['conc']} | {'yes' if r['agent'] else 'no'} | {r['n']} | "
              f"{r['p50']:.2f} | {r['p95']:.2f} | {r['errors']} | {r['busy']} |")
    return int(any(r["errors"] for r in rows if r["conc"] <= 4))


if __name__ == "__main__":
    raise SystemExit(main())
