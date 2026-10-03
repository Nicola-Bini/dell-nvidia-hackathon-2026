"""Run the whole CAC stack on a laptop with no Docker.

    cd services/owner
    uv run python dev/run_local.py            # database, seed, fake model, Serve API, Owner API
    uv run python dev/run_local.py --no-serve # database, seed, Owner API only

Postgres + pgvector is embedded (pgserver) and its data lives in ~/.cac-dev/pgdata, so a
second run keeps what you did. `--reset` wipes it. The processes use the repo's `.env` for
tokens and ports; only the two database URLs are overridden to point at the embedded server.
Ctrl+C stops everything. This is a development convenience: the box uses Docker.
"""

import argparse
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import time

import httpx
import pgserver
import psycopg
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "owner"))
DATA = pathlib.Path.home() / ".cac-dev" / "pgdata"
SEARCH_INDEXES = (
    "CREATE INDEX IF NOT EXISTS public_node_search_tsv_idx ON kg_public.node"
    " USING gin (to_tsvector('english', search_text))",
    "CREATE INDEX IF NOT EXISTS node_search_tsv_idx ON kg.node"
    " USING gin (to_tsvector('english', search_text))",
)


def load_env() -> dict[str, str]:
    """`.env` (created from `.env.example` if missing), then the process environment."""
    env_file, example = ROOT / ".env", ROOT / ".env.example"
    if not env_file.exists():
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    values = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return {**values, **os.environ}


def bootstrap(admin_uri: str, env: dict[str, str]) -> bool:
    """Create roles and schema on first run. Returns True when the database was new."""
    with psycopg.connect(admin_uri, autocommit=True) as conn:
        if conn.execute("SELECT to_regclass('kg.node')").fetchone()[0]:
            return False
        ddl = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
        ddl = ddl.replace(":'owner_pw'", f"'{env['CAC_OWNER_PASSWORD']}'")
        ddl = ddl.replace(":'serve_pw'", f"'{env['CAC_SERVE_PASSWORD']}'")
        conn.execute(ddl)
        for statement in SEARCH_INDEXES:
            conn.execute(statement)
    return True


def seed(owner_url: str, env: dict[str, str]) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    os.environ.update(OWNER_DATABASE_URL=owner_url, EMBED_BASE_URL=env.get("EMBED_BASE_URL", ""))
    from cac_common.settings import get_settings
    from seedlib import ROOT as SEED_ROOT
    from seedlib.build import build_graph
    from seedlib.db import seed_database

    get_settings.cache_clear()
    demo = SEED_ROOT / "demo" / "kenmore"

    def load(name: str) -> dict:
        return yaml.safe_load((demo / name).read_text(encoding="utf-8"))

    business, version, counts = seed_database(build_graph(load("seed.yaml"),
                                                          load("demo-overlay.yaml")))
    print(f"seeded {business}: graph_version={version}, {sum(counts.values())} nodes")


def spawn(name: str, cmd: list[str], cwd: pathlib.Path, env: dict[str, str]):
    print(f"starting {name}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=cwd, env=env)


def wait_for(url: str, name: str, seconds: int = 90) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                print(f"  {name} is up: {url}")
                return
        except httpx.HTTPError:
            time.sleep(1)
    print(f"  WARNING: {name} did not answer at {url} within {seconds}s")


def children(args: argparse.Namespace, env: dict[str, str]) -> list[tuple[str, list, object, str]]:
    """(name, command, cwd, health url) for each process to start."""
    serve_port, owner_port = env["SERVE_PORT"], env["OWNER_PORT"]
    owner = ("owner api", [sys.executable, "-m", "app.main"], ROOT / "services" / "owner",
             f"http://127.0.0.1:{owner_port}/healthz")
    if args.no_serve:
        return [owner]
    llm_port = env["LLM_BASE_URL"].rstrip("/").removesuffix("/v1").rsplit(":", 1)[-1]
    return [
        ("fake model", ["uv", "run", "tools/fake_llm/server.py", "--port", llm_port], ROOT,
         f"http://127.0.0.1:{llm_port}/v1/models"),
        ("serve api", ["uv", "run", "uvicorn", "cac_serve.main:app", "--host", "127.0.0.1",
                       "--port", serve_port], ROOT / "services" / "serve",
         f"http://127.0.0.1:{serve_port}/healthz"),
        owner,
    ]


def ports_in_use(env: dict[str, str], no_serve: bool) -> list[int]:
    """Ports this script needs that something is already listening on."""
    llm_port = int(env["LLM_BASE_URL"].rstrip("/").removesuffix("/v1").rsplit(":", 1)[-1])
    wanted = [int(env["OWNER_PORT"])] + ([] if no_serve else [int(env["SERVE_PORT"]), llm_port])
    busy = []
    for port in wanted:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                busy.append(port)
    return busy


def prepare_database(args: argparse.Namespace, env: dict[str, str]):
    """Start embedded Postgres, create and seed it on first run. Returns (server, urls)."""
    if args.reset and DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True, exist_ok=True)
    pg = pgserver.get_server(DATA, cleanup_mode="stop")
    admin = pg.get_uri()
    owner_url = admin.replace("postgres:@", f"cac_owner:{env['CAC_OWNER_PASSWORD']}@")
    serve_url = admin.replace("postgres:@", f"cac_serve:{env['CAC_SERVE_PASSWORD']}@")
    if not bootstrap(admin, env):
        print("database already set up; keeping its data (use --reset to start over)")
        return pg, owner_url, serve_url
    seed(owner_url, env)
    if not args.no_traffic:
        from app.demo import seed_traffic
        with psycopg.connect(owner_url, row_factory=psycopg.rows.dict_row) as conn:
            seed_traffic.seed(conn, env["CAC_BUSINESS_ID"])
        print("seeded demo traffic: 5 parking sessions, 12 gift card sessions")
    return pg, owner_url, serve_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--reset", action="store_true", help="wipe the local database first")
    parser.add_argument("--no-serve", action="store_true", help="skip the fake model and Serve")
    parser.add_argument("--no-traffic", action="store_true", help="skip the demo gap traffic")
    args = parser.parse_args()

    env = load_env()
    env.setdefault("SERVE_PORT", "8080")
    env.setdefault("OWNER_PORT", "8081")
    busy = ports_in_use(env, args.no_serve)
    if busy:
        print(f"Port(s) {busy} are already in use: the stack is probably already running. "
              "Stop it first (Ctrl+C in its terminal). Nothing was changed.")
        return 1
    pg, owner_url, serve_url = prepare_database(args, env)
    child_env = {**env, "OWNER_DATABASE_URL": owner_url, "SERVE_DATABASE_URL": serve_url,
                 "PYTHONPATH": "src" + os.pathsep + str(ROOT / "packages" / "cac_common")}
    procs = []
    try:
        for name, cmd, cwd, health in children(args, env):
            local_env = dict(child_env)
            if name == "owner api":
                local_env["PYTHONPATH"] = "."
            procs.append(spawn(name, cmd, cwd, local_env))
            wait_for(health, name)
        print(f"\nOwner inbox : http://127.0.0.1:{env['OWNER_PORT']}/owner/inbox"
              f"?token={env['OWNER_INBOX_TOKEN']}")
        print(f"Owner API   : http://127.0.0.1:{env['OWNER_PORT']}/docs"
              f"   (agent token: {env['OWNER_TOOLS_TOKEN']})")
        if not args.no_serve:
            print(f"Serve API   : http://127.0.0.1:{env['SERVE_PORT']}/healthz")
        print("Ctrl+C to stop.")
        signal.sigwait([signal.SIGINT]) if hasattr(signal, "sigwait") else time.sleep(10**9)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in reversed(procs):
            proc.terminate()
        pg.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
