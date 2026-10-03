"""Demo proof: the serving role cannot read the private graph, leads or the request log.

Run: uv run --project tests python scripts/permission_check.py
Exits 0 when every SELECT is refused with "permission denied".
"""

from __future__ import annotations

import sys
from pathlib import Path

# Importable without the editable install (see tests/pyproject.toml).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "cac_common"))

import psycopg  # noqa: E402
from cac_common.settings import get_settings  # noqa: E402

PRIVATE_TABLES = ("kg.node", "kg.edge", "kg.change", "ops.lead", "ops.intent_log")


def denied(conn: psycopg.Connection, table: str) -> str | None:
    """The refusal message for a SELECT on `table`, or None if the read succeeded."""
    try:
        conn.execute(f"SELECT * FROM {table} LIMIT 1")  # noqa: S608 (fixed table names)
    except psycopg.errors.InsufficientPrivilege as exc:
        conn.rollback()
        return str(exc).splitlines()[0]
    return None


def main() -> int:
    settings = get_settings()
    failures = 0
    with psycopg.connect(settings.serve_database_url) as conn:
        role = conn.execute("SELECT current_user").fetchone()[0]
        print(f"connected as {role}")
        for table in PRIVATE_TABLES:
            message = denied(conn, table)
            if message is None:
                print(f"FAIL  select * from {table}: the read succeeded")
                failures += 1
            else:
                print(f"ok    select * from {table}: {message}")
        public = conn.execute("SELECT count(*) FROM kg_public.node").fetchone()[0]
        print(f"ok    select count(*) from kg_public.node: {public} published nodes")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
