#!/usr/bin/env bash
# Start order from SCHEMA section 2, each step gated on a health check.
# Postgres, model server, Owner tools API, Serve API, then (P1) MCP. Exits non-zero on the
# first unhealthy step. Override start commands with OWNER_CMD / SERVE_CMD / MCP_CMD.
set -u
. "$(dirname "$0")/lib.sh"
rc=0

make -s db-up >"$LOGDIR/db.log" 2>&1
if make -s db-check >>"$LOGDIR/db.log" 2>&1; then echo "OK   postgres"
else echo "FAIL postgres"; exit 1; fi
# Seed is an upsert plus publish, safe on every start.
if make -s seed >"$LOGDIR/seed.log" 2>&1; then echo "OK   seed"
else echo "FAIL seed (see $LOGDIR/seed.log; an old volume needs make db-reset seed)"; exit 1; fi

# Serve's model: llama-server on :11436 (box/model.sh says why not Ollama directly).
box/model.sh >/dev/null || { echo "FAIL model (box/model.sh)"; exit 1; }
step model "http://127.0.0.1:${BOX_MODEL_PORT:-11436}/health" 120 || exit 1

if [ -n "${EMBED_BASE_URL:-}" ]; then step embedder "$EMBED_BASE_URL/models" 30 || exit 1
else echo "OK   embedder (full-text fallback, EMBED_BASE_URL empty)"; fi

owner_cmd=(${OWNER_CMD:-uv run --no-dev --directory services/owner python -m app.main})
step owner "http://127.0.0.1:$OWNER_PORT/openapi.json" 60 "${owner_cmd[@]}" || exit 1

# Widget and demo site: git-ignored builds the Serve API serves at /widget/, /embed.js, /site/.
for app in widget demo-site; do
  if [ -d "apps/$app" ] && [ ! -d "apps/$app/dist" ]; then
    (cd "apps/$app" && npm ci --silent && npm run -s build) >"$LOGDIR/build-$app.log" 2>&1 \
      && echo "OK   build $app" || echo "WARN build $app failed (see $LOGDIR/build-$app.log)"
  fi
done

serve_cmd=(${SERVE_CMD:-make serve SERVE_HOST=0.0.0.0})
step serve "http://127.0.0.1:$SERVE_PORT/healthz" 60 "${serve_cmd[@]}" || exit 1

if [ -n "${MCP_CMD:-}" ]; then step mcp "http://127.0.0.1:8090/health" 30 $MCP_CMD || rc=1; fi
[ $rc -eq 0 ] && echo "ALL UP"
exit $rc
