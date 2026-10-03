# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "httpx"]
# ///
"""Selection benchmark: the 30 intents through one small constrained completion each.

Straight at the model endpoint, at 1 and 4 concurrent. Prints median and p95 latency,
tokens per second and component accuracy. Run: uv run bench/selection_bench.py
"""
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("BOX_LLM_BASE_URL",
                      os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"))
MODEL = os.environ.get("BOX_LLM_MODEL", os.environ.get("LLM_MODEL", "qwen3.6:35b"))
COMPONENTS = ["MenuList", "AllergenNotice", "HoursCard", "Answer", "BookingForm",
              "CateringQuoteForm", "FormCard"]
SYSTEM = (
    "You pick one UI component for a bar's website visitor question. "
    "MenuList: food or drink items. AllergenNotice: allergy questions. HoursCard: opening "
    "hours. Answer: other factual answers. BookingForm: book a table. CateringQuoteForm: "
    "catering. FormCard: any other request form. Reply with JSON only."
)
SCHEMA = {"type": "object", "required": ["component"], "additionalProperties": False,
          "properties": {"component": {"type": "string", "enum": COMPONENTS}}}


def one(client: httpx.Client, text: str) -> tuple[float, int, str]:
    body = {"model": MODEL, "max_tokens": 40, "temperature": 0, "reasoning_effort": "none",
            "think": False,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "sel", "strict": True, "schema": SCHEMA}}}
    t0 = time.perf_counter()
    r = client.post(f"{BASE}/chat/completions", json=body, timeout=120)
    dt = time.perf_counter() - t0
    r.raise_for_status()
    j = r.json()
    picked = json.loads(j["choices"][0]["message"]["content"])["component"]
    return dt, j["usage"]["completion_tokens"], picked


def run(intents: list[dict], conc: int) -> dict:
    with httpx.Client() as client:
        one(client, "warm up")
        wall0 = time.perf_counter()
        with ThreadPoolExecutor(conc) as pool:
            res = list(pool.map(lambda i: one(client, i["text"]), intents))
        wall = time.perf_counter() - wall0
    lat = sorted(r[0] for r in res)
    scored = [(r, i) for r, i in zip(res, intents) if "component" in i["expect"]]
    correct = sum(r[2] == i["expect"]["component"] for r, i in scored)
    return {"concurrency": conc, "n": len(res), "median_s": round(statistics.median(lat), 3),
            "p95_s": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 3),
            "tokens_per_s": round(sum(r[1] for r in res) / wall, 1),
            "wall_s": round(wall, 2), "component_correct": f"{correct}/{len(scored)}"}


def main() -> int:
    intents = yaml.safe_load((ROOT / "demo/kenmore/intents.yaml").read_text())["intents"]
    print(f"model={MODEL} endpoint={BASE}")
    for conc in (1, 4):
        print(json.dumps(run(intents, conc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
