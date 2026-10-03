# Status: `nico` (Nico)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 | merged-pending (PR needs `gh auth login`) | — | `box/checks.sh` -> ALL CHECKS PASSED (embedder WARN, decision below) |
| wp2 | merged | PR in this branch | `uv run bench/selection_bench.py` -> table below |

## Measured numbers

Box: Dell GB10, aarch64, 121 GB unified memory (about 89 GB available with qwen3.6:35b loaded).

- Model server: **Ollama**, not vLLM. `http://127.0.0.1:11434/v1` (OpenAI-compatible).
  NemoClaw's onboard proxy for sandboxes: `0.0.0.0:11435`, seen from the sandbox as
  `http://host.openshell.internal:11435/v1`.
- Model id: `qwen3.6:35b` (qwen35moe, Q4_K_M, 22 GB). Also on disk: `nemotron-3-super:120b`,
  `qwen3.5:9b`. The `.env.example` id `nvidia/Qwen3.6-35B-A3B-NVFP4` does not exist here.
- Structured output (json_schema, strict) valid with `reasoning_effort: none`, `think: false`:
  0.12 to 2.3 s warm for a 7-token answer (first call 8 s cold load).
- Selection bench (30 intents, one constrained completion each, qwen3.6:35b, thinking off):
  1 concurrent: median 0.25 s, p95 0.30 s, 43.9 tok/s. 4 concurrent: median 0.96 s, p95 1.06 s,
  44.5 tok/s. Aggregate throughput does not rise: Ollama is serving one request at a time, so
  4 concurrent queue (4x latency). Crude 7-way component prompt: 23/28 correct (the real
  pipeline's prompt is Blake's).
- Embedder: **none on disk**. Vector length n/a.
- pgvector image `pgvector/pgvector:pg16` pulled.

## Decisions

- Embedder: none installed and no model downloads at the venue, so full-text fallback:
  `EMBED_BASE_URL` stays empty. Blake: keep `vector(1024)` column, leave it NULL.
- Box `.env`: `LLM_BASE_URL=http://127.0.0.1:11434/v1`, `LLM_MODEL=qwen3.6:35b`.
- `box/checks.sh` reads overrides `BOX_LLM_BASE_URL`, `BOX_LLM_MODEL`, `BOX_EMBED_*`.
- Port conflict: the OpenShell gateway listens on `127.0.0.1:8080` and `172.18.0.1:8080`,
  the Serve API's port. See `docs/team/requests/nico-to-blake-01-serve-port.md`.

- Concurrency: Ollama runs with OLLAMA_NUM_PARALLEL unset (effectively serial). Setting it
  needs the ollama service environment (sudo, a person). NEED_INPUT asked once; until then
  budget p95 about 1 s per queued model call and keep MODEL_MAX_INFLIGHT=4.

## Requests handled

## Blocked on

- `gh auth login` (a person) before any PR can be opened.
- `nemoclaw onboard --fresh` (sandbox `blake`) is running interactively in another terminal
  (pts/13) and holds the NemoClaw lock; wp3 waits for it. Sandbox-reachability check shows
  WARN until a sandbox exists.
