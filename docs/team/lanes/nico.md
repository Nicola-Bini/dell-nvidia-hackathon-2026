# Lane `nico`: the box and the agent

You own the Dell Pro Max with GB10 and the always-on agent that makes the product learn.
Much of this lane is run on the box itself. Paths: `box/`, `agent/`, `bench/`,
`services/mcp/`.

Read: PRD sections 3, 8 (Flow 3, Flow 2), 9 (rows A1 to A4, O3, X1, X2), 10, 11, 16
(first 30 minutes, cut lines), 18. SCHEMA sections 2, 8.6, 8.7. OWNERSHIP seams 5 to 8.
`docs/research/nvidia-stack.md` when a NemoClaw detail is unclear.

You are on a Pro plan: at most 2 subagents at a time, on `sonnet`.

First, find the box. If this machine is the box (`uname -m` is `aarch64`, `nvidia-smi`
works, `nemoclaw` is installed), work here. If not, ask the user once how to reach it
(`ssh` target), store that in `.env` as `CAC_BOX_SSH`, and run box commands through it.

## Work packages

| # | Package | Proof (one command, passing) | Unblocks |
|---|---|---|---|
| wp1 | **First-30-minute checks** (PRD section 16, items 2 to 9) as `box/checks.sh`: model answers; a structured-output call is valid with thinking off; embedder on disk and its vector length; free memory; pgvector image starts; sandbox can reach the host; concurrency setting. Results and decisions go in your status file under "Measured numbers" | `box/checks.sh` prints a PASS or FAIL line per item and the numbers | blake (model id, embedder, vector length) |
| wp2 | **Selection benchmark.** `bench/selection_bench.py`: the 30 texts in `demo/kenmore/intents.yaml` through one small constrained completion each, at 1 and 4 concurrent, straight at the model endpoint | Prints median and p95 latency and tokens per second; numbers in the status file | PRD latency targets |
| wp3 | **Agent says hello.** One OpenClaw agent in the NemoClaw sandbox, heartbeat 5 minutes, sends a message on the owner channel (local dashboard). Time one agent turn with one tool call | A message arrives; seconds per turn recorded | wp4 |
| wp4 | **Agent skill and instructions.** `agent/`: one skill wrapping je's Owner tools API with `OWNER_TOOLS_TOKEN`, and the agent's instructions for its two moves: ask the owner about the top gap and record the reply (`/owner/gaps/{id}/asked`, `/owner/answers` or `/owner/special-hours`, `/owner/publish`); or change the graph through `POST /owner/changes` with a reason and evidence. It reads topics and counts only | Against je's API: a seeded gap is asked and, after a reply, answered and published; a seeded gift-card topic yields a pending `create_label`, two `create_node` and one `create_component` change | gate 17:00 |
| wp5 | **Sandbox and recovery.** OpenShell policy allowing only the Owner tools API, the model endpoint and the owner channel; a script that shows a blocked egress attempt; `box/up.sh` and `box/recover.sh` (seam 7); heartbeat digest from `/owner/digest` | The blocked-egress script shows the refusal; `box/recover.sh` brings everything back to healthy | demo |
| wp6 | **Deploy and load test.** `origin/main` running on the box through `box/up.sh`. `bench/load_test.py` against `/v1/intent` at 1, 4 and 8 concurrent, once with an agent turn in flight | Latency table in the status file; no errors at 4 concurrent | gate 18:30 |
| wp7 | P1, only after the 18:30 gate: `services/mcp` from Anthropic's MCP Apps quickstart with the pins in SCHEMA 8.7, text-only `ask_restaurant` first, then the element from `apps/widget/dist-mcp/surface.html`, then the tunnel | From Claude: the question returns the element; a booking request creates a lead | Flow 2 |

## Working before the other lanes land

- Until je's API is merged, build wp4 against SCHEMA 8.6 with a mock in
  `agent/dev/mock_owner_api.py`. Switch to the real API as soon as je's wp1 to wp3 land,
  and delete the mock.
- Things only a person can do: ask the organizers the questions in PRD section 18, answer
  NemoClaw installer prompts, sign in to the tunnel and add the Claude connector. Ask for
  each once, as early as possible, then keep going on something else.
- Never download a model at the venue, and never load a second large model beside the
  first.

## Gates and cut lines (PRD section 16)

- **17:00**: both loops run on the box against seeded topics. If not, cut line 3 now: the
  agent does two jobs only (ask about the top gap; propose the gift-card type and form).
- Sandboxed agent cannot reach the Owner tools API over plain HTTP: register the same
  endpoints as a Streamable HTTP MCP server with NemoClaw (cut line 4) and file a request
  to `je`.
- Dashboard not reachable from a phone: use a messaging channel (cut line 5).
- **18:30**: Flow 1 and Flow 3 pass on the box. Only then wp7. If the MCP App does not
  render, ship text-only and show the element in the local test host (cut line 1).
