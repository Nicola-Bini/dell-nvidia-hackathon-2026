# Shared helpers for box scripts. Source, do not run.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.local/bin:$PATH"
[ -f .env ] && set -a && . ./.env && set +a
SERVE_PORT="${SERVE_PORT:-8082}"
OWNER_PORT="${OWNER_PORT:-8081}"
SANDBOX="${CAC_SANDBOX:-$(nemoclaw list --json 2>/dev/null | python3 -c 'import json,sys
s=json.load(sys.stdin)["sandboxes"];d=[x for x in s if x.get("isDefault")] or s
print(d[0]["name"] if d else "")' 2>/dev/null)}"
LOGDIR="${CAC_LOGDIR:-$HOME/.cache/cac}"; mkdir -p "$LOGDIR"

alive() { # any HTTP answer below 500 means the server is up (401 counts)
  local c; c=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "$1")
  [ "$c" -ge 100 ] && [ "$c" -lt 500 ]
}
wait_http() { # url, seconds
  local i; for ((i = 0; i < $2; i++)); do alive "$1" && return 0; sleep 1; done; return 1
}
step() { # name url seconds start-command...
  local name=$1 url=$2 secs=$3; shift 3
  if alive "$url"; then echo "OK   $name (already up)"; return 0; fi
  [ $# -gt 0 ] && nohup "$@" >"$LOGDIR/$name.log" 2>&1 &
  if wait_http "$url" "$secs"; then echo "OK   $name"; else echo "FAIL $name ($url)"; return 1; fi
}
