#!/usr/bin/env bash
# Shows the sandbox policy at work: allowed calls succeed, everything else is refused.
set -u
. "$(dirname "$0")/lib.sh"
[ -n "$SANDBOX" ] || { echo "no sandbox registered"; exit 1; }
try() { # label url expect(allow|deny)
  local code exp
  code=$(OPENSHELL_GATEWAY=nemoclaw openshell sandbox exec --name "$SANDBOX" -- \
    curl -s -m 8 -o /dev/null -w '%{http_code}' "$2" 2>/dev/null </dev/null)
  local verdict=denied; [[ "$code" =~ ^(2|3|4)[0-9][0-9]$ && "$code" != 403 ]] && verdict=allowed
  [ "$3" = allow ] && exp=allowed || exp=denied
  if [ "$verdict" = "$exp" ]; then echo "PASS $1: $verdict (HTTP $code)"
  else echo "FAIL $1: $verdict, expected $exp (HTTP $code)"; FAIL=1; fi
}
FAIL=0
try "owner API (allowed)"   "http://host.openshell.internal:8081/owner/digest" allow
try "owner API docs page"   "http://host.openshell.internal:8081/openapi.json" deny
try "internet: example.com" "https://example.com" deny
try "internet: github.com"  "https://github.com" deny
try "host database 54320"   "http://host.openshell.internal:54320" deny
try "serve API on host"     "http://host.openshell.internal:${SERVE_PORT:-8082}/v1/metrics" deny
try "model server (llama)"  "http://host.openshell.internal:11436/v1/models" deny
exit $FAIL
