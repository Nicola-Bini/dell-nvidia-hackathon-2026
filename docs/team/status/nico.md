# Status: `nico` (Nico)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 | merged | [#3](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/3) | `box/checks.sh` -> ALL CHECKS PASSED (embedder WARN, decision below) |
| wp2 | merged | [#4](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/4) | `uv run bench/selection_bench.py` -> median 0.25 s, p95 0.30 s at 1; 0.96/1.07 at 4 |
| wp3 | partial: agent ran in the sandbox; sandbox since lost; hello not sent | [#24](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/24) | `box/agent_install.sh` -> the sandboxed agent reads `/owner/digest` from je's API; `hermes chat -q` turn with one tool call: 23.7 s cold, **7.0 s warm**. Telegram hello: the owner sends it (see Blocked on) |
| wp4 | merged, proven on real APIs | [#7](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/7), [#23](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/23) | `box/demo_reset.sh && python3 -m unittest discover -s agent/tests -v` -> 3 OK against je's Owner API and the real Serve API on the box (15:45 ET): parking asked, answered, published, and "is there parking near you?" returns the owner's words; gift-card plan -> pending create_label, 2 create_node, create_component |
| wp5 | partial: egress and recovery proven; 5-minute heartbeat not scheduled | [#27](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/27) | `box/egress_demo.sh` -> 7 PASS (16:10 ET): `/owner/**` allowed; `/openapi.json` on the same port, example.com, github.com, the database, the Serve API and the model server all refused. `box/recover.sh` after killing the Owner API, Serve API and llama-server -> ALL UP in 24 s |
| wp6 | partial: deployed, load-tested | [#23](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/23), [#28](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/28) | `box/up.sh` -> ALL UP; `uv run bench/load_test.py -n 24` -> table below, 0 errors at 4 concurrent. Agent-turn-in-flight row missing (needs the sandbox) |
| wp7 (P1) | partial: server built and proven on a laptop, text-only; not on the box, no element, no tunnel | [#30](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/30) | `cd services/mcp && npm test` -> 10 pass, `npm run typecheck` clean. Live against the real Serve API on a laptop (16:30 ET): `request_booking` -> lead stored with channel `mcp`; `MCP_BASE_URL=... scripts/canary.py` -> 40 prompts, 89 responses, canary and goals in none. From Claude: not run (needs the tunnel and the connector, a person) |
| wp8 (owner's ask, 16:30) | built and proven on a laptop; not yet run by the model on the box | [#31](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/31) | `python3 -m unittest discover -s agent/tests -p test_grow.py` -> 10 OK (fake API, a bike-shop graph). Against je's real Owner API code (its pytest harness, embedded Postgres): `next-task` returns a `classify` packet without locked labels; `apply` with one change of each kind (`create_edge`, `create_label`, `create_node`, `create_edge_type`, `add_prop`, a ListCard and a FormCard `create_component`) -> 0 refused; a repeat is skipped |

## Still missing (16:35 ET)

In order. Each line says who it waits on.

1. **The agent sandbox is gone.** At 16:22 `nemoclaw blake3 rebuild` failed ("Rebuild
   recreate failed"); `nemoclaw list` shows no sandboxes (backup in
   `~/.nemoclaw/rebuild-backups/blake3`). Waits on Nico: onboard again (Hermes, Telegram).
   Then `box/agent_install.sh` puts the skill, instructions and the `/owner/**` network
   rule back in one command. Everything below the sandbox (Postgres, model, Owner API,
   Serve API) is up and unaffected.
2. **wp3: "hello" on the owner channel (Telegram).** The agent's permission guard refuses to
   message a real account, so Nico sends the first one from the sandbox:
   `hermes send -t telegram:<owner user id> "Hello from your CAC agent"`.
3. **wp5: the 5-minute heartbeat** (digest, then move 1, then move 2 from
   `agent/HEARTBEAT.md`) is not scheduled in Hermes cron. It delivers to Telegram, so it
   waits on 1 and 2.
4. **wp6: load-test row with an agent turn in flight.** Waits on 1:
   `uv run bench/load_test.py --agent-cmd "box/agent_turn.sh digest"`.
5. **18:30 gate**, Flow 1 and Flow 3 acceptance on the box: Flow 1 passes now (the widget
   and site are served from the box's LAN address); Flow 3 waits on 1.
6. **wp7 (P1) MCP server**, built ahead of the gate on a laptop so only box work is left:
   a. On the box: `git pull`, `box/up.sh` (now starts it on `:8090`, as a WARN-only step).
      Not yet run there.
   b. The element: waits on cj's wp6 (`npm run build:mcp` -> `apps/widget/dist-mcp/
      surface.html`). Until then `ask_restaurant` is text-only (cut line 1); the server
      picks the file up with no restart.
   c. The tunnel and the Claude connector: a person (steps in `services/mcp/README.md`).
      After the 18:30 gate.

## 17:00 gate: both loops on the box, run by the sandboxed agent (16:20 ET): PASS

From `box/demo_reset.sh` (seed plus 12 gift-card and 5 parking sessions), with the Hermes
agent in sandbox `blake3`, through je's Owner API and the real Serve API:

| Step | Agent turn | Result |
|---|---|---|
| Move 1 (`box/agent_turn.sh move1`) | 5.8 s | "5 visitors asked about parking. I have nothing confirmed. What should I tell them?" (gift cards skipped: a plan covers it) |
| Owner reply recorded (`box/agent_turn.sh answer gap_parking "..."`) | 8.3 s | FAQ in the owner's words, published; "where can I park" on the Serve API returns it as `Answer` |
| Move 2 (`box/agent_turn.sh move2`) | 10.6 s | pending, one tap: `create_label` GiftCard, 2 `create_node`, `create_component` |

Cut line 3 not needed. Owner-channel delivery (Telegram) is the one part not shown: see
Blocked on.

## Measured numbers

Box: Dell GB10, aarch64, 121 GB unified memory (about 89 GB available with qwen3.6:35b loaded).

- **Model for the Serve API: `llama-server` on `:11436`** (`box/model.sh`), the same binary
  and model blob Ollama uses, `qwen3.6:35b` (qwen35moe, Q4_K_M, 22 GB), 4 slots of 8k context,
  flash attention off, 512 batches. `LLM_BASE_URL=http://127.0.0.1:11436/v1`.
- Why not Ollama (`:11434`): Ollama 0.35.1 runs this model with flash attention on and 1024
  batches, and llama.cpp's CUDA MUL_MAT crashes ("illegal memory access") about one request
  in four: 16 crashes in an hour, each followed by an 8 to 9 s reload, which is past the
  Serve API's 6 s model timeout (the visitor gets the busy fallback). Same crash with the
  MTP speculative decoding off and with CUDA graphs off. With flash attention off and 512
  batches: 0 crashes in 120+ requests. Generation 78 tok/s versus 44 through Ollama.
- NemoClaw's inference proxy for sandboxes is still Ollama: `0.0.0.0:11435`, seen from the
  sandbox as `http://host.openshell.internal:11435/v1`.
- Also on disk: `nemotron-3-super:120b`, `qwen3.5:9b`. `qwen3.5:9b` is stable on Ollama but
  picked the right component for 3 of 30 of Blake's intents: rejected.
- Embedder: **none on disk**. Full-text fallback.
- Blake's 30 intents on the box, real model (`CAC_INTENTS_REAL_MODEL=1 uv run pytest -m
  intents`, 15:45 ET): **29 of 30**; the one miss is "is there parking nearby?" answering
  the FAQ the wp4 proof had just created (database not reset between runs), so effectively
  30 of 30. `scripts/canary.py`: ok, canary and goals in no response.
  `scripts/permission_check.py`: ok.
- Selection bench (wp2, crude prompt, Ollama): 1 concurrent median 0.25 s, p95 0.30 s;
  4 concurrent 0.96 / 1.06 s.
- Load test, `POST /v1/intent`, every text new (no cache), 24 requests per row, 15:40 ET:

  | concurrent | p50 s | p95 s | errors | busy fallbacks |
  |---|---|---|---|---|
  | 1 | 0.66 | 1.82 | 0 | 1 |
  | 4 | 2.05 | 6.04 | 0 | 3 |
  | 8 | 0.03 | 2.20 | 0 | 20 (by design: `MODEL_MAX_INFLIGHT=4`) |

  Same test on Ollama before the switch: 9 of 24 busy at 1 concurrent, 17 of 24 at 4.
  `/v1/metrics` after the intents run: p50 12 ms, p95 516 ms, cache hit rate 0.71.

7. **wp8: one `grow` turn by the sandboxed model.** Everything around the model is proven;
   whether qwen3.6 writes a valid change list from a task packet is not. Waits on 1. Then:
   `box/agent_install.sh && box/agent_turn.sh grow` (expect a `summary` line), and
   `box/up.sh` starts `box/agent_loop.sh`, one `grow` turn every 5 minutes.

## Decisions

- **Move 3, grow the graph** (owner's ask at 16:30: the agent only ran one hardcoded
  gift-card plan and never read the graph). `cac_owner.py next-task` picks one task per
  heartbeat from the live schema, graph and topics, in rotation classify, topics, classify,
  invent: `classify` hands the model 8 nodes of one type with every small type as tags and
  the edge types as seen in the graph; `topics` hands it the most-asked unanswered topic
  nothing was built for; `invent` hands it the types no element shows and what was already
  proposed. The model writes a JSON list of changes; `cac_owner.py apply` orders them
  (types before nodes before edges), drops anything the agent ever proposed (rejected
  included), adds the evidence and posts them. Same lesson as the 79 s free-form turn: code
  chooses and checks, the model only judges. No business, type or topic is named anywhere
  in `agent/cac_grow.py` or the `grow` prompt (a test asserts it).
- A full owner inbox (more than 6 pending changes) holds back `topics` and `invent`;
  `classify` keeps going because its tags are auto tier in `balanced`.
- `ask-top-gap` now also skips a topic the agent already built something for, not only
  topics a file in `plans/` covers. The gift-card plan and moves 1 and 2 are unchanged.
- `/owner/graph/search` returns 25 nodes with no offset, so `nodes_of` splits a full page by
  id prefix (`mi_a`, `mi_b`, ...) until pages come back short. Request filed to je for
  `limit` and `after`; the split goes when that lands.
- `box/agent_loop.sh` runs `grow` every `HEARTBEAT_SECONDS` (300); `box/up.sh` starts it when
  a sandbox exists (`CAC_AGENT_LOOP=0` keeps it off). `move1` is not in the loop by default:
  it marks a gap `asked`, which is only right once Telegram delivers the question.
  **Risk for the demo:** every auto-tier change publishes and pre-warms (je's API replays
  the top intents through the model). If visitor latency suffers, set `CAC_AGENT_LOOP=0` or
  raise `HEARTBEAT_SECONDS`.

- wp7 was written before the 18:30 gate, on Blake's laptop (16:30 ET), because items 1 to 5
  above all wait on the sandbox and on Nico at the box, and nothing else in the lane could
  move. It touched nothing on the box. Deploying it, the tunnel and the connector still wait
  for the gate.
- MCP server: every tool call is its own anonymous session (`mcp_<uuid>`), since an assistant
  sends no visitor id; the Serve API's channel cap (10 leads an hour on `mcp`) is the limit
  that applies. It logs tool, outcome and milliseconds only. It refuses to start unless
  `SERVE_BASE_URL` is loopback. A public Host reaches `/mcp` only; `/health` is local.
- `ask_restaurant`'s description leaves out "(Cambridge, MA)": `/v1/bootstrap` gives name and
  tagline only, and the Kenmore is in Boston. `get_business_profile` returns what the public
  API has: name, tagline, services (the nav) and hours. Cuisine, address and price range are
  not in any Serve API response.
- `submit_form` (FormCard, for example the gift-card form) has no MCP tool in SCHEMA 8.7, so
  in the MCP App build those forms cannot submit. cj: hide the submit or show "on the site".
- `box/up.sh`: the MCP step warns and never fails the start, so a P1 fault cannot break the
  `box/recover.sh` proof.

- Heartbeat turns use one explicit command per prompt (`agent/HEARTBEAT.md`). A free-form
  "do move 1" turn wandered for 79 s, ran out of turns and tried hand-built changes (all
  refused, nothing written). Explicit prompts take 6 to 11 s.

- OpenShell rule `cac_owner_api` uses explicit GET/POST `/owner/**` rules and no access
  preset: the `read-write` preset silently allowed every path on the port (the egress demo
  caught `/openapi.json` getting through). `box/agent_install.sh` removes and re-adds it.
- `box/lib.sh` starts services with `setsid` and no inherited descriptors; before, a caller
  piping `box/up.sh` hung until the services exited.

- Agent sandbox is `blake3` (owner's call, 15:55): NemoClaw with the **Hermes** runtime, not
  OpenClaw; owner channel is **Telegram** (cut line 5 in effect). `box/agent_install.sh`
  uploads `agent/` to `/sandbox/agent`, the skill to `~/.hermes/skills/cac-owner`, appends
  `agent/INSTRUCTIONS.md` to `SOUL.md` under a `<!-- CAC -->` marker (idempotent), writes
  `agent.env` (mode 600, git-ignored) and adds OpenShell rule `cac_owner_api`: only
  GET/POST `/owner/**` on `host.openshell.internal:8081`. Policy version 4 is live.
- The agent's model goes through NemoClaw to Ollama, so Ollama loads a second copy of
  qwen3.6:35b beside llama-server's (22 GB each; 31 GB still free, above the 16 GB floor).
  Ollama's crash affects agent turns, not visitors; an agent turn is retried on the next
  heartbeat.

- Serve's model is `llama-server` on :11436 (above). `box/up.sh` starts it via `box/model.sh`.
  Ollama keeps serving the NemoClaw sandbox; it holds no model until the agent calls it.
- Embedder: none installed and no model downloads at the venue, so full-text fallback:
  `EMBED_BASE_URL` stays empty.
- Box `.env` (git-ignored): `LLM_BASE_URL=http://127.0.0.1:11436/v1`, `LLM_MODEL=qwen3.6:35b`,
  `SERVE_PORT=8082`, `SERVE_BASE_URL=http://127.0.0.1:8082`.
- `box/up.sh` order: Postgres, `make seed`, model, embedder (skipped), Owner API
  (`uv run --no-dev`: je's dev group pulls `pgserver`, which has no aarch64 wheel), Serve API
  gated on `/healthz`.
- `box/demo_reset.sh` wipes the box database back to the seed plus je's demo traffic. Load
  tests are logged as visitor traffic and create topics, so reset after every load test.
- Agent: a gap that a plan in `agent/plans/` covers (gift cards) is not put to the owner as a
  question; it goes to move 2 (a graph change). Other gaps are asked.
- The wp4 mock (`agent/dev/mock_owner_api.py`) is deleted: je's API is merged.

## Requests handled

- `blake-to-nico-01-serve-start` (15:50): `box/up.sh` starts `cac_serve.main:app` via
  `make serve SERVE_HOST=0.0.0.0`, seeds first, gates on `/healthz`. The 30 intents, canary
  and permission proofs ran on the box; results above.
- `blake-to-nico-02-gift-card-plan` (15:50): the `create_component` change sends
  `rail_label: "Request a gift card"`; fields are name and contact (text, required) and
  amount (select, $25 or $50, required), each with a label. Accepted by je's API.

## Blocked on

- Items 1 and 2 of "Still missing": both need Nico (sandbox onboarding, first Telegram message).
- NEED_INPUT: how does a laptop reach the box (`ssh` target for `CAC_BOX_SSH`)? Without it
  items 1 to 5 and 6a can only be done by the person at the box.
- 6c: tunnel sign-in and adding the Claude connector (a person), after the 18:30 gate.
