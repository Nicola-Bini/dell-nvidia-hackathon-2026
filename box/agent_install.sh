#!/usr/bin/env bash
# Installs the CAC agent into the NemoClaw sandbox (Hermes runtime): the Owner tools client
# and plans at /sandbox/agent, the skill at ~/.hermes/skills/cac-owner, the instructions
# in SOUL.md's CAC section, and the network rule for the Owner tools API.
set -eu
. "$(dirname "$0")/lib.sh"
[ -n "$SANDBOX" ] || { echo "no sandbox"; exit 1; }
export OPENSHELL_GATEWAY=nemoclaw
os() { openshell "$@" </dev/null; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/agent"; cp -r agent/cac_owner.py agent/cac_grow.py agent/plans agent/INSTRUCTIONS.md "$tmp/agent/"
printf 'OWNER_BASE_URL=http://host.openshell.internal:%s\nOWNER_TOOLS_TOKEN=%s\n' \
  "$OWNER_PORT" "${OWNER_TOOLS_TOKEN:?set in .env}" >"$tmp/agent/agent.env"
os sandbox upload "$SANDBOX" "$tmp/agent" /sandbox/ >/dev/null
os sandbox upload "$SANDBOX" agent/skill/cac-owner /sandbox/.hermes/skills/ >/dev/null
os sandbox exec --name "$SANDBOX" -- sh -c 'chmod 600 /sandbox/agent/agent.env
  python3 - <<PY
from pathlib import Path
soul = Path("/sandbox/.hermes/SOUL.md")
base = soul.read_text().split("<!-- CAC -->")[0].rstrip()
cac = Path("/sandbox/agent/INSTRUCTIONS.md").read_text()
soul.write_text(base + "\n\n<!-- CAC -->\n" + cac)
PY'
ep="host.openshell.internal:$OWNER_PORT::rest:enforce:allowed-ip=172.16.0.0/12"
# Remove first: a re-add merges into the old rule. No access preset (it would allow all paths).
os policy update "$SANDBOX" --remove-rule cac_owner_api --wait >/dev/null 2>&1 || true
os policy update "$SANDBOX" --rule-name cac_owner_api --add-endpoint "$ep" \
  --add-allow "host.openshell.internal:$OWNER_PORT:GET:/owner/**" \
  --add-allow "host.openshell.internal:$OWNER_PORT:POST:/owner/**" \
  --binary /usr/bin/python3.13 --binary /opt/hermes/.venv/bin/python3 --binary /usr/bin/curl \
  --wait >/dev/null
os sandbox exec --name "$SANDBOX" -- python3 /sandbox/agent/cac_owner.py digest
