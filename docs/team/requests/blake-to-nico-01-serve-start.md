# Request: blake to nico: start the Serve API with the right module, and seed first

**Need.** `box/up.sh` starts the Serve API with `uvicorn app.main:app`. The Serve API's
module is `cac_serve.main:app` (package `services/serve/src/cac_serve`), so the default
command fails to import. The box database also needs the seed before the Serve API answers
anything but 503.

**Proposal.** In `box/up.sh`:

1. After Postgres is healthy: `make seed` (safe to re-run; it upserts and publishes). A
   volume created before PR #5 lacks `pg_trgm`: run `make db-reset seed` once.
2. Serve API: `SERVE_HOST=0.0.0.0 SERVE_PORT=8082 make serve`, or directly
   `uv run --project services/serve uvicorn cac_serve.main:app --host 0.0.0.0 --port "$SERVE_PORT"`.
   Gate on `GET /healthz` (always 200; `status` is `ok` or `degraded`, with `database`,
   `model`, `embedder`, `graph_version`).
3. Box `.env`: `LLM_BASE_URL=http://127.0.0.1:11434/v1`, `LLM_MODEL=qwen3.6:35b`,
   `EMBED_BASE_URL=` (empty), `SERVE_PORT=8082`, `SERVE_BASE_URL=http://127.0.0.1:8082`, and
   `CAC_ALLOWED_ORIGINS` listing every origin the demo site is opened from (for example
   `http://<box-ip>:8082`). The Serve API refuses to start if `LLM_BASE_URL` is not this
   machine.

**Then, for the 17:00 gate, on the box** (please put the results in your status file):

```bash
cd services/serve && CAC_INTENTS_REAL_MODEL=1 uv run pytest -m intents -s   # 30 intents, real model
uv run --project tests python scripts/canary.py                              # privacy proof
uv run --project tests python scripts/permission_check.py
curl -s http://127.0.0.1:8082/v1/metrics                                     # latency p50/p95
```

On a laptop with Ollama `qwen2.5:7b` the first command gives 28 of 30. If `qwen3.6:35b`
gives fewer than 27, send me the "wrong:" lines it prints and I will tune the prompt.

**Why.** The 17:00 gate is measured on the box with the real model.
**By.** Before your integration package (wp6).
