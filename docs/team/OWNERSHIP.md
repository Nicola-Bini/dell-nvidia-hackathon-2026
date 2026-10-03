# Ownership and seams

Who owns which paths, and the interfaces between lanes. `tools/lanes.conf` is the
machine-readable copy of the path table; keep the two in step. Blake owns this file.

## Paths

| Lane | Paths | Contents |
|---|---|---|
| `blake` | `db/` | `schema.sql` (SCHEMA section 4, verbatim), init script, later DDL |
| | `demo/kenmore/` | The seed for graph and demo site: `seed.yaml`, `demo-overlay.yaml`, `intents.yaml` (the 30 intents) |
| | `fixtures/` | Golden surfaces, `surfaces/index.json`, `validate.py` |
| | `packages/cac_common/` | Shared Python: settings, search text, embedding, publish |
| | `services/serve/` | Serve API, port 8080, role `cac_serve` |
| | `tools/` | `lane-check`, `fake_llm` |
| | `scripts/`, `tests/` | Seed loader entry, permission check, canary, end-to-end tests |
| | root files, `docs/PRD.md`, `docs/SCHEMA.md`, `docs/team/OWNERSHIP.md`, `docs/team/lanes/`, `docs/team/prompts/` | Contracts and shared config |
| `je` | `services/owner/` | Owner tools API and inbox page, port 8081, role `cac_owner` |
| `cj` | `apps/widget/` | Widget, `embed.js`, overlay, the single-file MCP App build |
| | `apps/demo-site/` | Static demo site generated from the seed |
| `nico` | `box/` | Box checks, start and recovery scripts, OpenShell policy, egress demo |
| | `agent/` | The OpenClaw agent: instructions, skill, heartbeat |
| | `bench/` | Selection benchmark, load test |
| | `services/mcp/` | MCP server, port 8090 (P1) |
| each lane | `docs/team/status/<lane>.md`, `docs/team/requests/<lane>-*` | Its own status and its own requests |

The three Pro lanes are sized alike. If a different person has the box in front of them,
swap names, not paths: change the Person column in `AGENTS.md` and use the other prompt.

## Seams

Each seam has one owner who publishes it and consumers who build against it. Until the
owner's side is merged, a consumer works against the contract with a mock in its own lane.

### 1. Database (owner: blake; consumers: je, nico)

- `make db-up` starts Postgres with pgvector on `127.0.0.1:54320`, database `cac`, with
  `db/schema.sql` applied. `make db-reset` wipes it. `make db-check` proves `cac_serve`
  cannot read `kg`, `ops.lead` or `ops.intent_log`.
- Port 54320, not SCHEMA's 5432, so a Postgres already running on a laptop does not clash.
  Always connect through `SERVE_DATABASE_URL` or `OWNER_DATABASE_URL` from `.env`.
- The demo business is The Kenmore, a real bar. Its data is in `demo/kenmore/`: site
  facts in `seed.yaml`, demo-only assumptions and the UI catalog in `demo-overlay.yaml`.
  This replaces the fictional restaurant in PRD section 18 and the single seed file in
  SCHEMA section 9. Read `demo/kenmore/README.md` for where the site does not fit the
  schema (hours past midnight, items in two sections, two prices).
- `make seed` (blake, wp1) applies `seed.yaml`, then the overlay, as approved public
  nodes, and publishes.
- The embedding column is `vector(1024)`. If the box's embedder differs, blake changes it.

### 2. Shared Python package (owner: blake; consumer: je)

`packages/cac_common`, installed by path (`uv add --editable ../../packages/cac_common`).
Its public surface, fixed now so `je` can code against it before it lands:

| Call | Behaviour |
|---|---|
| `cac_common.settings.get_settings()` | Typed view of the environment variables in `.env.example` |
| `cac_common.graph.reindex_node(conn, node_id)` | Rebuilds `search_text` from `name` and the label's `public_props`, and sets `embedding` (NULL when `EMBED_BASE_URL` is empty: full-text fallback). Call after every node create or update |
| `cac_common.graph.publish(conn, business_id) -> int` | Calls `kg.publish()` and returns the new graph version |

Neither call commits: the caller owns the transaction. `reindex_node` raises `LookupError`
for an unknown node. If an editable install is not importable on your machine (macOS can
flag a venv under `~/Desktop` as hidden, and Python 3.12.13 then skips its `.pth` files),
add `pythonpath = ["../../packages/cac_common"]` under `[tool.pytest.ini_options]` and set
`PYTHONPATH` the same way when you run the service.

### 3. Serve API (owner: blake; consumers: cj, nico, je)

- Port: `SERVE_PORT`, 8080 on laptops and **8082 on the box** (the OpenShell gateway holds
  8080 there). Never hard-code the port: every caller uses `SERVE_BASE_URL`, and the widget
  uses the origin it was loaded from.
- Endpoints, pipeline and rules: SCHEMA section 8.5. Surface shape: section 8.4. One golden
  file per case in `fixtures/surfaces/`, and `fixtures/surfaces/index.json` maps intent
  text to its file. Conventions: `fixtures/README.md`.
- First merged as a stub (blake, wp2): `/v1/intent` answers the texts in
  `fixtures/surfaces/index.json` with their golden files and everything else with the off-topic surface.
- `GET /v1/metrics` returns exactly:
  `{ "latency_ms": { "p50": 0, "p95": 0 }, "cache_hit_rate": 0.0, "model_calls": 0,
  "model_inflight": 0, "graph_version": 1, "leads_captured": 0, "cta_shown": 0,
  "cta_clicked": 0, "model_host": "127.0.0.1:8000" }`.
- A goal button click is counted when the widget opens the preset with
  `GET /v1/view/{preset}?src=cta`.
- Internal callers set `X-CAC-Channel: mcp` or `X-CAC-Channel: prewarm`. The header is
  honoured only from a loopback client; every other request is channel `web`.
- Static files, served if the directory exists and 404 otherwise: `/widget/` from
  `apps/widget/dist/`, `/embed.js` from `apps/widget/dist/embed.js`, `/site/` from
  `apps/demo-site/dist/`.

### 4. Widget and demo site (owner: cj; consumers: blake, nico)

- `npm run build` in `apps/widget` writes `dist/` (with `embed.js`); `npm run build:mcp`
  writes `dist-mcp/surface.html`, one file with no external origins (P1, for `nico`).
- `npm run build` in `apps/demo-site` reads `demo/kenmore/seed.yaml` and writes `dist/`. The
  page carries schema.org JSON-LD for the menu and hours, nav links marked
  `data-cac-preset`, and the two-line embed from SCHEMA section 7.
- The widget talks through a `transport` with `intent(text)`, `view(preset)` and
  `action(name, payload)` (SCHEMA section 8.7): a `fetch` build, a fixture mock for
  development, and the MCP host build.

### 5. Owner tools API (owner: je; consumers: nico, blake)

- Endpoints, tiers and credentials: SCHEMA section 8.6. `GET /openapi.json` is the live
  contract. The agent sends `Authorization: Bearer $OWNER_TOOLS_TOKEN`; the inbox uses
  `OWNER_INBOX_TOKEN`.
- `GET /owner/inbox` is an HTML page served by this API; `GET /owner/inbox.json` is the
  same data as JSON.
- `GET /owner/topics` is what turns new `ops.intent_log` rows into topics and
  `KnowledgeGap` nodes.
- `POST /owner/publish` publishes, then replays the top 20 logged intents and
  the texts in `demo/kenmore/intents.yaml` through `POST $SERVE_BASE_URL/v1/intent` with
  `X-CAC-Channel: prewarm`.

### 6. Model and embedder (owner: nico on the box, blake on laptops)

- Everything reads `LLM_BASE_URL`, `LLM_MODEL`, `EMBED_BASE_URL`, `EMBED_MODEL`.
- Laptops: `tools/fake_llm` (blake, wp2) is an OpenAI-compatible stub on `127.0.0.1:8000`
  that returns a schema-valid selection from keyword rules. Embeddings fall back to
  full-text search.
- Box: `nico` records the real endpoint, model id, embedder, vector length and the measured
  latencies in `docs/team/status/nico.md`. Blake reads them from there.
- Measured on the box: Ollama at `http://127.0.0.1:11434/v1`, model `qwen3.6:35b`, no
  embedder (full-text fallback, `EMBED_BASE_URL` empty). The Serve API sends
  `response_format` with a JSON Schema and turns thinking off with both
  `reasoning_effort: "none"` (Ollama) and `chat_template_kwargs` (vLLM).

### 7. The box (owner: nico; consumers: everyone at integration)

- `box/up.sh` runs the start order from SCHEMA section 2, each step gated on a health
  check. `box/recover.sh` restarts Docker, the OpenShell gateway and the sandbox, then
  calls `box/up.sh`.
- `nico` deploys `origin/main` to the box and reports what is running in the status file.

### 8. MCP server (owner: nico; consumers: none; P1)

Holds no database credentials. Every tool calls the Serve API with `X-CAC-Channel: mcp`.
Serves `apps/widget/dist-mcp/surface.html` as `ui://cac/surface.html`.
