#!/usr/bin/env bash
# Start order from SCHEMA section 2, each step gated on a health check.
# Postgres, model server, Owner tools API, Serve API, then (P1) MCP. Exits non-zero on the
# first unhealthy step. Override start commands with OWNER_CMD / SERVE_CMD / MCP_CMD.
set -u
. "$(dirname "$0")/lib.sh"
rc=0

make -s db-up >"$LOGDIR/db.log" 2>&1
if make -s db-check >>"$LOGDIR/db.log" 2>&1; then echo "OK   postgres"; else echo "FAIL postgres"; exit 1; fi

step model "${BOX_LLM_BASE_URL:-http://127.0.0.1:11434/v1}/models" 60 || exit 1

if [ -n "${EMBED_BASE_URL:-}" ]; then step embedder "$EMBED_BASE_URL/models" 30 || exit 1
else echo "OK   embedder (full-text fallback, EMBED_BASE_URL empty)"; fi

owner_cmd=(${OWNER_CMD:-uv run --project services/owner uvicorn app.main:app \
  --host 0.0.0.0 --port "$OWNER_PORT"})
step owner "http://127.0.0.1:$OWNER_PORT/openapi.json" 60 "${owner_cmd[@]}" || exit 1

serve_cmd=(${SERVE_CMD:-uv run --project services/serve uvicorn app.main:app \
  --host 0.0.0.0 --port "$SERVE_PORT"})
step serve "http://127.0.0.1:$SERVE_PORT/v1/metrics" 60 "${serve_cmd[@]}" || exit 1

if [ -n "${MCP_CMD:-}" ]; then step mcp "http://127.0.0.1:8090/health" 30 $MCP_CMD || rc=1; fi
[ $rc -eq 0 ] && echo "ALL UP"
exit $rc
