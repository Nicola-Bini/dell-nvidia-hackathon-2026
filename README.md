# CAC: Chats, Agents, Context

A local agent a small business owns. It turns the business's website into a knowledge
graph and serves it two ways: as an interface to visitors, and as tools to AI assistants.
Everything runs on one Dell Pro Max with GB10: the database, the model, the agent, the
APIs. No cloud model, no cloud deployment. Built at the Dell x NVIDIA AI Hackathon, Boston,
3 October 2026, by four people building in parallel.

The demo business is **The Kenmore**, a restaurant at 476 Commonwealth Avenue, Boston.

- Product: [docs/PRD.md](docs/PRD.md)
- Contracts: [docs/SCHEMA.md](docs/SCHEMA.md)
- Rules for coding agents: [AGENTS.md](AGENTS.md)
- Who owns what: [docs/team/OWNERSHIP.md](docs/team/OWNERSHIP.md)
- What each lane shipped, with proof commands and results:
  [blake](docs/team/status/blake.md), [je](docs/team/status/je.md),
  [cj](docs/team/status/cj.md), [nico](docs/team/status/nico.md)

## What it does

**A visitor asks, the site answers from the graph.** A panel on the business's own site
takes a question ("is there parking nearby?", "anything gluten-free?"). A local model picks
which components to show (answer, menu list, hours, booking form, gift-card form) from a
schema built out of the graph. The model only chooses; code binds the real data into the
components, so a dish, a price or an hour is never invented. When the graph has no answer,
the panel says so ("We haven't confirmed that yet") and logs the gap.

**The owner fills the gaps.** Gaps become topics in an owner inbox. The owner answers in
their own words, publishes, and the next visitor who asks gets that answer marked verified.
No restart, no re-deploy. Raw visitor text never reaches the owner or the agent: they see
aggregated topics only.

**An agent grows the graph on its own.** A NemoClaw (Hermes) agent in an OpenShell sandbox
runs a heartbeat. Each beat it does one explicit move: put the most-asked unanswered topic
to the owner, propose a new component for a recurring need (a gift-card form), or read the
graph and propose a new classification (tag every dish that is gluten-free, add a type no
element shows yet). Changes go through a tier function: small ones apply, structural ones wait
for one tap from the owner, and some are locked to the owner for good. The agent can only
call `GET`/`POST /owner/**` on one port; the sandbox refuses everything else.

**An assistant can use the same business.** An MCP server exposes the Serve API as tools
(`get_business_profile`, `ask_restaurant`, `get_view`, `request_booking`,
`request_catering_quote`), so Claude or another assistant can ask The Kenmore questions
and request a booking. Leads from it are stored with channel `mcp`.

**The "find us" map (wp9, this branch).** The owner tells the agent where parking is. The
agent places the named garages on the demo site's own street map, and the widget draws
those places as numbered pins on that map. The map is built from an OpenStreetMap extract
of Kenmore Square (`scripts/demo_recording/build_map.py`, data (c) OpenStreetMap
contributors, ODbL).

## How it fits together

```
 visitor on the demo site                    owner (inbox, owner channel)
        |  embed.js -> widget iframe                |
        v                                           v
  Serve API :8080 (box 8082) <---------- Owner tools API + inbox :8081
  role cac_serve, read-only on              role cac_owner, change engine,
  published graph, writes leads             approve / reject / revert / verify
        |                                           ^
        v                                           |  GET/POST /owner/** only
  local model (llama-server :11436,           NemoClaw agent (Hermes) in an
  qwen3.6:35b) via LLM_BASE_URL               OpenShell sandbox, heartbeat
        |                                           |
        +--------------- Postgres + pgvector -------+
                          (kg, ops schemas)
  MCP server :8090 -> Serve API (channel mcp, loopback only)
```

Python 3.12, FastAPI, psycopg 3 with raw SQL; Vite, React, TypeScript; Node 22. Models are
reached only through `LLM_BASE_URL` and `EMBED_BASE_URL`, and the Serve API refuses to start
unless the model host is local.

## Privacy, enforced

These are checked by proofs, not just promised (PRD section 10).

- The Serve API connects only as `cac_serve`, which is denied on the private graph, the
  leads table and the intent log (`make db-check`: 3 of 3 denied;
  `scripts/permission_check.py`: every private read denied).
- A canary string and a goal planted in visitor prompts appear in no response, no log and no
  agent-visible endpoint (`scripts/canary.py`: 40 prompts, 47 responses, no leak).
- Only the owner credential can approve, revert or verify. The agent token gets 403 on all
  of them, and on the owner inbox.
- Customer nodes and goals are never returned to the agent token.
- Card numbers and SSNs submitted to a form are rejected and never stored.
- On the box, the agent's sandbox reaches `/owner/**` and nothing else: `box/egress_demo.sh`
  shows the owner API allowed and `/openapi.json`, example.com, github.com, the database,
  the Serve API and the model server all refused (7 PASS).

## Measured

Last recorded in the lane status files (the newest entries are from 16:35 ET).

| What | Result |
|---|---|
| Box | Dell GB10, aarch64, 121 GB unified memory |
| Model | `qwen3.6:35b` (Q4_K_M, 22 GB) on `llama-server`, 4 slots, about 78 tok/s |
| 30 curated intents, real model on the box | 29 of 30 right component, 30 of 30 schema-valid; the one miss was a stale-database artifact |
| Same intents, real 7B model on a laptop | 29 of 30 right, 30 of 30 valid |
| `/v1/intent` load, new text each time | 1 concurrent: p50 0.66 s, p95 1.82 s. 4 concurrent: p50 2.05 s, p95 6.04 s. No errors |
| `/v1/metrics` after the intents run | p50 12 ms, p95 516 ms, cache hit rate 0.71 |
| One agent turn with one tool call | 5.8 to 10.6 s warm (explicit heartbeat prompts) |
| Selection benchmark | median 0.25 s, p95 0.30 s at 1 concurrent |

Why `llama-server` and not Ollama for the Serve API: Ollama 0.35.1 crashed the CUDA kernel
about one request in four on this model (16 crashes in an hour, each followed by an 8 to 9
second reload). With flash attention off and 512 batches, `llama-server` had 0 crashes in
120+ requests and generates 78 tok/s versus 44 through Ollama. Details in
[the nico status file](docs/team/status/nico.md).

## What was built, by lane

| Lane | Built | Proof |
|---|---|---|
| Blake | Graph write side and seed; Serve API with the full intent pipeline (slots, cache, retrieval, one constrained model call, binder); actions and leads with rate limits; safety and steer; privacy proofs; end to end tests; fake model for laptops | `cd services/serve && uv run pytest` 354 passed; `uv run --project tests pytest tests/graph` 79 passed; `tests/e2e` 10 passed, 1 xfailed |
| Je | Owner tools API: two credentials, approval-tier function, change engine for all ten actions, approve/reject/revert/verify, owner inbox (HTML and JSON), topics and gaps, special hours, publish with pre-warm, demo traffic seeding, one-command local stack | `cd services/owner && uv run pytest` 156 passed |
| CJ | Widget shell, a component per golden surface, interaction (forms, cart, goal buttons), `embed.js` (about 2.6 kB), demo site built from the seed, metrics overlay and busy/error/offline states | `npm test` in `apps/widget` 67 passed; in `apps/demo-site` 5 passed |
| Nico | Box checks, deploy scripts, model server, agent skill and instructions, sandboxed agent, egress policy, recovery, load test, MCP server, graph-growing heartbeat | `box/up.sh` ALL UP; `box/egress_demo.sh` 7 PASS; `services/mcp` `npm test` 10 passed; `agent/tests` `test_grow.py` 10 OK |

## Not finished

Taken from the status files; check them for anything newer.

- **The agent sandbox (`blake3`) was lost at 16:22** when `nemoclaw blake3 rebuild` failed.
  `box/agent_install.sh` puts the skill, instructions and network rule back in one command
  once the sandbox is onboarded again. The two agent loops were proven in it at 16:20
  (move 1 in 5.8 s, owner reply in 8.3 s, move 2 in 10.6 s) before it went.
- **Telegram delivery** of the agent's messages was never shown. The first "hello" has to be
  sent by the owner from the sandbox.
- **The 5-minute heartbeat** is not scheduled in Hermes, and `box/agent_loop.sh` (the
  graph-growing `grow` turn) has never been run by the model on the box. Everything around
  the model is proven; whether `qwen3.6` writes a valid change list from a task packet is not.
- **MCP on the box:** built and proven against the real Serve API on a laptop, text-only.
  Not deployed on the box, no MCP App element yet, no tunnel or Claude connector (a person
  has to add those).
- **wp9 map and demo recording** (`demo/kenmore/map.*`, `MapList.tsx`, `scripts/demo_recording/`)
  are on the `blake/wp9-parking-map-demo` branch and not merged. The widget's map component
  has no test of its own yet; the widget suite is still 67 tests.
- No embedder on the box (no model downloads at the venue), so retrieval uses full-text
  search. `EMBED_BASE_URL` is empty.
- JSON-LD ingest and the slot-masked cache from the lane plan (wp9 in
  [lanes/blake.md](docs/team/lanes/blake.md)) were not started.

## Run it

Needs Docker, `uv`, Node 22 and the GitHub CLI. On a laptop with no Docker, use the
one-command stack below.

```bash
make hooks env        # lane guard on push; .env from .env.example
make db-up db-check   # Postgres + pgvector on 127.0.0.1:54320; privacy check
make fixtures-check   # seed and golden fixtures agree
make seed             # load The Kenmore into the graph and publish (safe to re-run)
make fake-llm         # laptops only: stand-in model on 127.0.0.1:8000 (own terminal)
make serve            # Serve API on SERVE_PORT (8080; the box uses 8082)
```

The widget and demo site are static builds that the Serve API mounts at `/widget/`,
`/embed.js` and `/site/`:

```bash
(cd apps/widget && npm ci && npm run build)
(cd apps/demo-site && npm ci && npm run build)   # also copies the map if demo/kenmore/map.* exists
```

**Laptop, no Docker:** `cd services/owner && uv run python dev/run_local.py --reset` starts
an embedded Postgres, loads the seed and demo gap traffic, then the fake model (8000), Serve
API (8080) and Owner API (8081), and prints the inbox URL with the owner token.

**On the box:** `box/checks.sh` (first-30-minute checks), `box/up.sh` (Postgres, seed,
model, Owner API, Serve API, MCP, agent loop if a sandbox exists), `box/recover.sh`,
`box/demo_reset.sh` (back to the seed plus demo traffic; run it after any load test),
`box/egress_demo.sh`, `uv run bench/load_test.py -n 24`.

**MCP server:** `cd services/mcp && npm ci && npm test`; see
[services/mcp/README.md](services/mcp/README.md) for the tunnel and connector steps.

**Demo recording:** `scripts/demo_recording/stack.sh start` wipes `~/.cac-dev/pgdata`, seeds,
adds demo traffic and runs a stack on ports 8110, 8180 and 8181 with `CAC_AUTONOMY=free`.
`uv run --with playwright python scripts/demo_recording/record.py` then records the
"site learns from a gap" storyboard. It needs Chrome and ffmpeg.

### Proofs

| Command | Expect |
|---|---|
| `uv run --project tests pytest tests/graph` | 79 passed |
| `cd services/serve && uv run pytest` | 354 passed |
| `cd services/serve && uv run pytest -m intents` | 15 passed: 30 of 30 valid, 30 of 30 right (fake model) |
| `CAC_INTENTS_REAL_MODEL=1 uv run pytest -m intents` (in `services/serve`, with `LLM_BASE_URL`) | the same 30 intents on a real model |
| `uv run --project tests pytest tests/e2e` | 10 passed, 1 xfailed (needs the Serve API, the Owner API and the built widget) |
| `uv run --project tests python scripts/permission_check.py` | every private read denied |
| `uv run --project tests python scripts/canary.py` | exit 0, no leak (needs `make serve`) |
| `cd services/owner && uv run pytest` | 156 passed |
| `cd apps/widget && npm test` | 67 passed |
| `uv run --with pytest --with jsonschema pytest tools/fake_llm` | 49 passed |
| `tools/lane-check` | PASS |

## Team and lanes

Four people each built one lane with their own coding agent. The one rule: change only
files in your lane (`tools/lanes.conf`, enforced by `tools/lane-check` on every push), so
branches could not conflict. Cross-lane needs went through request files in
`docs/team/requests/`.

| Person | Lane | Start prompt | Per-package prompts | Work packages |
|---|---|---|---|---|
| Blake | Graph, pipeline, integration | [prompts/blake.md](docs/team/prompts/blake.md) | [blake-packages.md](docs/team/prompts/blake-packages.md) | [lanes/blake.md](docs/team/lanes/blake.md) |
| Je | Owner tools API and inbox | [prompts/je.md](docs/team/prompts/je.md) | [je-packages.md](docs/team/prompts/je-packages.md) | [lanes/je.md](docs/team/lanes/je.md) |
| CJ | Widget, demo site, overlay | [prompts/cj.md](docs/team/prompts/cj.md) | [cj-packages.md](docs/team/prompts/cj-packages.md) | [lanes/cj.md](docs/team/lanes/cj.md) |
| Nico | The box, the agent, MCP | [prompts/nico.md](docs/team/prompts/nico.md) | [nico-packages.md](docs/team/prompts/nico-packages.md) | [lanes/nico.md](docs/team/lanes/nico.md) |

## Layout

```
db/                 schema.sql (SCHEMA section 4), search indexes, container init script
demo/kenmore/       the seed: The Kenmore's site facts, demo overlay, 30 intents, map
fixtures/           one golden surface per case
packages/cac_common shared Python (settings, search text, embedding, publish)
services/serve      Serve API, port 8080 (box 8082), role cac_serve
services/owner      Owner tools API and inbox, port 8081, role cac_owner
services/mcp        MCP server, port 8090
apps/widget         the panel, embed.js, overlay, map list
apps/demo-site      static demo site built from the seed
agent/              the NemoClaw agent: skill, instructions, heartbeat, graph growth
box/  bench/        box scripts and egress policy; selection and load benchmarks
scripts/            seed, privacy proofs, demo recording and map builder
tests/              graph and end to end tests (their own uv project)
tools/              lane-check, fake_llm
docs/team/          ownership, lane plans, start prompts, status, requests
```
