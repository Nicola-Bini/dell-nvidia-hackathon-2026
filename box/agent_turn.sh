#!/usr/bin/env bash
# Runs one agent turn in the sandbox from a prompt in agent/HEARTBEAT.md, or a reply:
#   box/agent_turn.sh move1|move2|digest
#   box/agent_turn.sh answer <gap_id> "<owner's exact reply>"
# Prints the agent's reply and the seconds the turn took.
set -u
. "$(dirname "$0")/lib.sh"
export OPENSHELL_GATEWAY=nemoclaw
if [ "$1" = answer ]; then
  prompt="The owner replied to your question about $2: \"$3\"
Record it word for word by running exactly:
python3 /sandbox/agent/cac_owner.py answer $2 \"$3\"
Then reply with one short line for the owner confirming it is live."
else
  prompt=$(awk -v h="## $1" '$0==h{f=1;next} /^## /{f=0} f' agent/HEARTBEAT.md)
  [ -n "$prompt" ] || { echo "no prompt '$1' in agent/HEARTBEAT.md"; exit 2; }
fi
t0=$(date +%s.%N)
openshell sandbox exec --name "$SANDBOX" -- hermes chat -Q --yolo -s cac-owner --max-turns 4 \
  -q "$prompt" </dev/null 2>&1 | grep -vE "Warning: Unknown|tirith|^$|^session_id"
echo "[turn $(echo "$(date +%s.%N) - $t0" | bc | cut -c1-5) s]"
