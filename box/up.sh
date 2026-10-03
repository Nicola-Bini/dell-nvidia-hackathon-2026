#!/usr/bin/env bash
# Start order from SCHEMA section 2, each step gated on a health check.
# Postgres, model server, Owner tools API, Serve API, then (P1) MCP. Exits non-zero on the
# first unhealthy P0 step. Override start commands with OWNER_CMD / SERVE_CMD / MCP_CMD.
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

# MCP server (P1, Flow 2). Never fails the start: Flow 1 and Flow 3 do not depend on it.
# It serves the element once apps/widget/dist-mcp/surface.html exists, text-only before.
MCP_PORT="${MCP_PORT:-8090}"
if [ -d services/mcp ] && command -v npm >/dev/null; then
  if [ -d apps/widget/node_modules ] && [ ! -f apps/widget/dist-mcp/surface.html ]; then
    (cd apps/widget && npm run -s --if-present build:mcp) >"$LOGDIR/build-widget-mcp.log" 2>&1
  fi
  [ -d services/mcp/node_modules ] \
    || (cd services/mcp && npm ci --silent) >"$LOGDIR/build-mcp.log" 2>&1
  mcp_cmd=(${MCP_CMD:-env MCP_PORT=$MCP_PORT SERVE_BASE_URL=http://127.0.0.1:$SERVE_PORT
    npm --prefix services/mcp run -s start})
  step mcp "http://127.0.0.1:$MCP_PORT/health" 30 "${mcp_cmd[@]}" \
    || echo "WARN mcp not up (see $LOGDIR/mcp.log); Flow 2 only"
fi
# The agent's standing loop (move 3, grow the graph). Never fails the start: it needs the
# sandbox, which only a person can onboard. CAC_AGENT_LOOP=0 keeps it off.
if [ "${CAC_AGENT_LOOP:-1}" = 1 ] && [ -n "$SANDBOX" ]; then
  if pgrep -f box/agent_loop.sh >/dev/null; then echo "OK   agent loop (already up)"
  else
    setsid nohup box/agent_loop.sh >"$LOGDIR/agent_loop.log" 2>&1 </dev/null &
    echo "OK   agent loop (log: $LOGDIR/agent_loop.log)"
  fi
else echo "SKIP agent loop (no sandbox, or CAC_AGENT_LOOP=0)"; fi
[ $rc -eq 0 ] && echo "ALL UP"
exit $rc
