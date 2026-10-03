#!/usr/bin/env bash
# After a reboot or crash: restart Docker, the OpenShell gateway and the sandbox, then run
# box/up.sh. NemoClaw does not restart on its own. Needs no sudo when the user is in the
# docker group; if Docker is down and cannot be started, the script says so.
set -u
. "$(dirname "$0")/lib.sh"

docker info >/dev/null 2>&1 || { sudo -n systemctl start docker 2>/dev/null || true; }
if docker info >/dev/null 2>&1; then echo "OK   docker"
else echo "FAIL docker (start it: sudo systemctl start docker)"; exit 1; fi

openshell status >/dev/null 2>&1 || nemoclaw gateway start >/dev/null 2>&1 || true
if openshell status >/dev/null 2>&1; then echo "OK   openshell gateway"
else echo "FAIL openshell gateway"; exit 1; fi

if [ -n "$SANDBOX" ]; then
  timeout 180 nemoclaw "$SANDBOX" recover >"$LOGDIR/recover.log" 2>&1 \
    || timeout 180 nemoclaw "$SANDBOX" start >>"$LOGDIR/recover.log" 2>&1
  if OPENSHELL_GATEWAY=nemoclaw openshell sandbox exec --name "$SANDBOX" -- true \
      </dev/null >/dev/null 2>&1; then echo "OK   sandbox $SANDBOX"
  else echo "FAIL sandbox $SANDBOX (see $LOGDIR/recover.log)"; exit 1; fi
else echo "WARN no sandbox registered yet"; fi

exec "$(dirname "$0")/up.sh"
