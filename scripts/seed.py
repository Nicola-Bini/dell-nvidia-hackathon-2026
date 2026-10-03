"""Load the demo business into the graph and publish it.

Run from the repo root: `make seed` (uv run --project tests python scripts/seed.py).
Applies demo/kenmore/seed.yaml, then demo-overlay.yaml, as approved `seed` rows for
CAC_BUSINESS_ID, connecting with OWNER_DATABASE_URL. Safe to re-run: every write is an
upsert and nothing is deleted.
"""

from __future__ import annotations

import sys

import yaml
from seedlib import ROOT
from seedlib.build import build_graph
from seedlib.db import seed_database

DEMO = ROOT / "demo" / "kenmore"


def _load(name: str) -> dict:
    return yaml.safe_load((DEMO / name).read_text(encoding="utf-8"))


def main() -> int:
    graph = build_graph(_load("seed.yaml"), _load("demo-overlay.yaml"))
    business_id, version, counts = seed_database(graph)
    per_label = " ".join(f"{label}={count}" for label, count in counts.items())
    print(
        f"seed: {business_id} graph_version={version} nodes={sum(counts.values())} "
        f"edges={len(graph.edges)} {per_label}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
