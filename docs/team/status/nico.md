# Status: `nico` (Nico)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 | merged | [#3](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/3) | `box/checks.sh` -> ALL CHECKS PASSED (embedder WARN, decision below) |
| wp2 | merged | [#4](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/4) | `uv run bench/selection_bench.py` -> median 0.25 s, p95 0.30 s at 1; 0.96/1.07 at 4 |
| wp3 | partial: agent runs in the sandbox, hello not yet sent | this PR | `box/agent_install.sh` -> the sandboxed agent reads `/owner/digest` from je's API; `hermes chat -q` turn with one tool call: 23.7 s cold, **7.0 s warm**. Telegram hello: the owner sends it (see Blocked on) |
| wp4 | merged, proven on real APIs | [#7](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/7), [#23](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/23) | `box/demo_reset.sh && python3 -m unittest discover -s agent/tests -v` -> 3 OK against je's Owner API and the real Serve API on the box (15:45 ET): parking asked, answered, published, and "is there parking near you?" returns the owner's words; gift-card plan -> pending create_label, 2 create_node, create_component |
| wp5 | partial | [#12](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/12) | `box/up.sh` -> ALL UP on the real stack (postgres, seed, model, owner, serve). Sandbox parts (`box/egress_demo.sh`, `box/recover.sh`, policy apply) unproven: need the NemoClaw lock |
| wp6 | partial: deployed, load-tested | [#23](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/23) | `box/up.sh` -> ALL UP; `uv run bench/load_test.py -n 24` -> table below, 0 errors at 4 concurrent. Agent-turn-in-flight row waits on wp3 |

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

## Decisions

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

- wp3 hello on Telegram: sending a message to the owner's account was refused by the agent's
  permission guard; the owner sends it once (command in the 16:05 handoff), then the agent
  can use `hermes send -t telegram:<owner id>`.
