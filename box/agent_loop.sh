#!/usr/bin/env bash
# Keeps the agent working. Every HEARTBEAT_SECONDS (default 300) it runs the turns in
# AGENT_LOOP_TURNS (default: grow) through box/agent_turn.sh, until killed.
#   box/agent_loop.sh                                  # foreground
#   AGENT_LOOP_TURNS="move1 grow" box/agent_loop.sh    # also ask the owner about the top gap
# move1 is off by default: it marks a gap as asked, which is only right once the question
# is delivered to the owner channel. box/up.sh starts this loop when a sandbox exists.
set -u
. "$(dirname "$0")/lib.sh"
[ -n "$SANDBOX" ] || { echo "no sandbox: onboard it, then run box/agent_install.sh"; exit 1; }
every="${HEARTBEAT_SECONDS:-300}"
while :; do
  for turn in ${AGENT_LOOP_TURNS:-grow}; do
    echo "== $(date '+%F %T') $turn"
    timeout "${AGENT_TURN_TIMEOUT:-240}" box/agent_turn.sh "$turn" \
      || echo "turn $turn failed or timed out ($?)"
  done
  sleep "$every"
done
