# CAC: Chats, Agents, Context

A local agent a small business owns. It turns the business's website into a knowledge
graph and serves it two ways: as an interface to visitors, and as tools to AI assistants.
Everything runs on one Dell Pro Max with GB10: the database, the model, the agent, the
APIs. No cloud model, no cloud deployment. Built for the Dell x NVIDIA AI Hackathon, Boston,
3 October 2026.

The demo business is **The Kenmore**, a restaurant at 476 Commonwealth Avenue, Boston.

- Product requirements: [docs/PRD.md](docs/PRD.md)
- Schema and wire contracts: [docs/SCHEMA.md](docs/SCHEMA.md)

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

**The "find us" map (not merged yet).** The owner tells the agent where parking is. The
agent places the named garages on the demo site's own street map, and the widget draws
those places as numbered pins on that map. The map is built from an OpenStreetMap extract
of Kenmore Square (`scripts/demo_recording/build_map.py`, data (c) OpenStreetMap
contributors, ODbL).

## Architecture

### The system

```
  THE BOX (Dell Pro Max GB10). Nothing on it calls a cloud.

  visitor's browser    customer's assistant    owner (inbox, channel)    NemoClaw agent
  demo site + widget   (Claude, ...)                                     (OpenShell sandbox)
        |                    | tunnel: /mcp only         |                       |
        |                    v                           |                       |
        |             +--------------+                   |                       |
        |             | MCP server   |                   | owner token           | agent token
        |             | :8090        |                   | approve, reject,      | GET/POST
        |             +------+-------+                   | revert, verify        | /owner/** only
        |                    | loopback, channel=mcp     |                       |
        v                    v                           v                       v
  +-------------------------------------+      +-------------------------------------+
  | Serve API   :8080 (box 8082)        |      | Owner tools API + inbox   :8081     |
  | role cac_serve                      |<-----| role cac_owner                      |
  | reads kg_public, inserts log+leads  |      | change engine, approval tiers,      |
  +------+----------------------+-------+      | publish + pre-warm                  |
         |                      |              +----------------+--------------------+
         | one constrained      | SQL                           | SQL
         | completion           |                               |
         v                      v                               v
  +-------------+     +----------------------------------------------------------+
  | local model |     | Postgres + pgvector                                      |
  | llama-server|     |  kg         full graph, drafts, goals, gaps (owner only) |
  | :11436      |     |  kg_public  published projection (serve reads this)      |
  | qwen3.6:35b |     |  ops        intent log, cache, leads                     |
  +-------------+     +----------------------------------------------------------+
```

The arrow from the Owner tools API to the Serve API is the pre-warm: after every publish it
replays the top 20 logged intents through `/v1/intent`, so the first visitor after a change
hits a warm cache.

Two things never cross a line on this picture. The Serve API has no grant on `kg`, so a
visitor path cannot reach a goal, a customer or a lead. The agent's sandbox reaches the Owner
tools API and nothing else: not the database, not the Serve API, not the model server, not
the internet.

| Process | Stack | Port | Database role | Reachable from |
|---|---|---|---|---|
| Serve API | Python 3.12, FastAPI, psycopg 3, raw SQL | 8080 on laptops, 8082 on the box | `cac_serve` | Visitors; the MCP server on loopback |
| Owner tools API and inbox | Python, FastAPI | 8081 | `cac_owner` | The sandboxed agent and the owner's browser. Never tunnelled |
| MCP server | Node 22 | 8090 | none | The tunnel, `/mcp` only |
| Widget, `embed.js` | Vite, React, TypeScript | served by the Serve API at `/widget/` and `/embed.js` | none | A browser iframe |
| Postgres + pgvector | Docker (laptops can use an embedded one) | 127.0.0.1 | none | Local processes |
| Model server | `llama-server` on the box (Ollama crashed on this model); `tools/fake_llm` on laptops | 11436 on the box, 8000 on laptops | none | The Serve API |
| Agent | NemoClaw with the Hermes runtime, in an OpenShell sandbox | none | none | Owner channel |

There is no ORM on the Serve API: `cac_serve` can insert into the log and lead tables but not
read them, and an ORM's `RETURNING` fails without read permission.

### A visitor question

The model chooses. Code writes every word and number the visitor sees.

```
text ─▶ validate ─▶ normalize + ─▶ cache lookup ──hit──────────────────────┐
        1–300 chars   slots         (hash, slots, graph version)           │
                      (dates,            │ miss                            │
                       party size)       ▼                                 ▼
                              retrieve: entry nodes + fixed        re-bind the cached
                              expansion templates (no model-       selection against the
                              written queries)                     current graph
                                     │                                     │
                                     ▼                                     │
                              build a JSON schema from what was            │
                              retrieved: only these components and         │
                              these ids are legal                          │
                                     │                                     │
                                     ▼                                     │
                              ONE model call, no tools, constrained        │
                              output, validated, one retry                 │
                                     │                                     │
                                     ▼                                     ▼
                              binder: pull real facts from the ──▶ Surface ──▶ log every request
                              graph snapshot, add badges, drop      (views of      (kind, gap_topic;
                              anything unsafe                       components)    never raw text out)
```

- A text that only names a preset ("See the menu", a nav label) skips the model entirely.
- Safety is in the binder, not the prompt. An unverified diet is never a badge, an allergen
  question never gets a dish list, and an answer that binds to nothing is served as a gap.
- When the graph has no answer, the surface says so and the request is logged as a gap with a
  topic. The model never writes visitor-facing text.
- If the model is slow or down, the visitor gets an ordinary "busy" surface with a way out.
  The Serve API warms the model at start-up and caps concurrent model calls.

### The publish boundary

```
 kg  (owner and agent write here)            kg_public  (the only thing visitors read)
 ┌───────────────────────────────┐  publish() ┌───────────────────────────────┐
 │ public, private, draft nodes  │ ─────────▶ │ approved public nodes only,   │
 │ goals, gaps, customers,       │  copies an │ and only props the label      │
 │ proposals, notes              │  allowlist │ registry names                │
 └───────────────────────────────┘            └───────────────────────────────┘
```

Nothing is public until someone marks it so and the owner approves it. A private prop left on
a public node (a supplier, a margin) is dropped at publish. A publish takes effect on the next
request, with no restart. The label registry, the edge registry and the component catalog are
rows in the database, so the agent can add a node type, an edge type or a new element without a
migration.

### The agent's loop

Every five minutes the agent does one explicit move. Code chooses and checks; the model only
judges. (A free-form "do move 1" turn wandered for 79 seconds and tried hand-built changes;
explicit single-command prompts take 6 to 11 seconds.)

| Move | What happens |
|---|---|
| 1. Ask | Read `/owner/gaps`, put the most-asked unanswered topic to the owner on the owner channel |
| 2. Build | A topic a plan covers (gift cards) becomes a graph change: a new type, nodes, and a request form |
| 3. Grow | `next-task` picks one task from the live graph and topics, in rotation: `classify` (tag eight nodes of one type), `topics`, `classify`, `invent` (a type no element shows yet). The model returns a change list; code orders it, drops anything ever proposed before, and posts it |

Each change goes to `POST /owner/changes`. The API, not the agent, assigns the approval tier:

| Tier | Meaning |
|---|---|
| `auto` | Applied and published now |
| `one_tap` | Written to the private graph as a draft; goes public when the owner approves |
| `locked` | Refused with a reason, and recorded |

`CAC_AUTONOMY` (`cautious`, `balanced`, `free`) moves changes between `auto` and `one_tap`.
In every mode, marking anything `verified_by_owner` and touching goals, customers, leads or
raw visitor text are locked: only the owner credential can verify, and only the owner
credential can approve, reject or revert. When the owner answers a gap, the answer is stored
in their words, published, and served as `Answer` with the verified mark. Every change
records its `before`, so a revert restores the old text.

### The assistant path

The MCP server holds no database credentials. Each tool is a call to the Serve API on the
same machine with `X-CAC-Channel: mcp`. The Serve API takes the channel from the caller, never
from the request body, and ignores it when a forwarding header is present, so traffic through
a tunnel cannot pass as `mcp` or `prewarm`. Each tool call is its own anonymous session, leads
from it are capped at 10 an hour, and the log records tool, outcome and milliseconds only.

### What the contracts pin down

The wire formats (selection, slots, binder, surface, the three APIs), the DDL, the label and
edge registries and the component catalog are in [docs/SCHEMA.md](docs/SCHEMA.md). The
privacy rules and the product reasoning are in [docs/PRD.md](docs/PRD.md) (section 10 for
privacy). Models are reached only through `LLM_BASE_URL` and `EMBED_BASE_URL`, and the Serve
API refuses to start unless the model host is local. One business per box: every process reads
`CAC_BUSINESS_ID` and no request carries a business id.

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

Measured on the box and on laptops during the build. The last measurements were taken at about 16:35 ET on 3 October.

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
120+ requests and generates 78 tok/s versus 44 through Ollama.

## What is built

| Component | What it does | Proof |
|---|---|---|
| Graph and seed | Schema, label and edge registries, seed of The Kenmore (175 public nodes: 110 dishes, 13 menu sections, 15 FAQs, 4 services, hours and special hours, and more), publish into `kg_public` | `uv run --project tests pytest tests/graph` 79 passed |
| Serve API | Full intent pipeline (slots, cache, retrieval, one constrained model call, binder), presets, actions and leads with rate limits, safety and steer rules, metrics | `cd services/serve && uv run pytest` 354 passed |
| Owner tools API and inbox | Two credentials, approval-tier function, change engine for all ten actions, approve, reject, revert, verify, owner inbox (HTML and JSON), topics and gaps, special hours, publish with pre-warm, demo traffic seeding | `cd services/owner && uv run pytest` 156 passed |
| Widget and demo site | A component per surface, forms, cart, goal buttons, `embed.js` (about 2.6 kB), demo site built from the seed, metrics overlay, busy, error and offline states | `npm test` 67 passed in `apps/widget`, 5 in `apps/demo-site` |
| Agent | Skill, instructions and a heartbeat with three moves (ask, build, grow), meant to run every five minutes, run in an OpenShell sandbox with an egress policy | `agent/tests` 3 OK on the real APIs; `test_grow.py` 10 OK |
| The box | Health checks, one-command deploy, recovery, model server, load test | `box/up.sh` ALL UP; `box/egress_demo.sh` 7 PASS |
| MCP server | Five tools over the Serve API, text-only for now | `cd services/mcp && npm test` 10 passed |
| Privacy proofs | Canary, permission check, end to end suite | `scripts/canary.py`, `scripts/permission_check.py`, `tests/e2e` 10 passed, 1 xfailed |

## Where it stands

What is not finished, as of the last measurements above.

- **The agent sandbox was lost at 16:22** when a NemoClaw rebuild failed.
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
- **The map and the demo recording** (`demo/kenmore/map.*`, `MapList.tsx`, `scripts/demo_recording/`)
  are on a separate branch and not merged. The widget's map component
  has no test of its own yet; the widget suite is still 67 tests.
- No embedder on the box (no model downloads at the venue), so retrieval uses full-text
  search. `EMBED_BASE_URL` is empty.
- JSON-LD ingest of the site and the slot-masked cache were not started.

## Run it

Needs Docker, `uv` and Node 22. On a laptop with no Docker, use the
one-command stack below.

```bash
make env              # .env from .env.example
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
tools/              fake_llm, the stand-in model for laptops
docs/               product requirements, schema contracts, research
```
