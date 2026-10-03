#!/usr/bin/env bash
# First-30-minute checks (PRD section 16). One PASS/FAIL/WARN line per item, with numbers.
# Env: LLM_BASE_URL, LLM_MODEL, EMBED_BASE_URL, EMBED_MODEL, OWNER_BASE_URL, CAC_DB_PORT.
set -u
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
export PATH="$HOME/.local/bin:$PATH"

# On the box the model server is Ollama; its OpenAI-compatible API lives on :11434/v1.
# The Serve API's model is llama-server on :11436 (box/model.sh). Never point this at Ollama
# (:11434): that would load a second copy of the model.
LLM_BASE_URL="${BOX_LLM_BASE_URL:-http://127.0.0.1:11436/v1}"
LLM_MODEL="${BOX_LLM_MODEL:-qwen3.6:35b}"
EMBED_BASE_URL="${BOX_EMBED_BASE_URL:-http://127.0.0.1:11434/v1}"
EMBED_MODEL="${BOX_EMBED_MODEL:-bge-m3}"
FAILS=0
pass() { echo "PASS $1: $2"; }
fail() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }
warn() { echo "WARN $1: $2"; }
now() { date +%s.%N; }

# 1. Model answers
t0=$(now)
r=$(curl -s -m 120 "$LLM_BASE_URL/chat/completions" -d "{\"model\":\"$LLM_MODEL\",\"max_tokens\":8,
 \"messages\":[{\"role\":\"user\",\"content\":\"Say OK\"}],\"reasoning_effort\":\"none\"}")
dt=$(echo "$(now) - $t0" | bc)
if echo "$r" | grep -q '"choices"'; then pass model "$LLM_MODEL answered at $LLM_BASE_URL in ${dt}s"
else fail model "no answer from $LLM_BASE_URL ($LLM_MODEL)"; fi

# 2. Structured output valid with thinking off
t0=$(now)
r=$(curl -s -m 120 "$LLM_BASE_URL/chat/completions" -d "{\"model\":\"$LLM_MODEL\",\"max_tokens\":50,
 \"reasoning_effort\":\"none\",\"think\":false,
 \"messages\":[{\"role\":\"user\",\"content\":\"Pick red or blue. JSON only.\"}],
 \"response_format\":{\"type\":\"json_schema\",\"json_schema\":{\"name\":\"c\",\"strict\":true,
 \"schema\":{\"type\":\"object\",\"properties\":{\"color\":{\"type\":\"string\",
 \"enum\":[\"red\",\"blue\"]}},\"required\":[\"color\"]}}}}")
dt=$(echo "$(now) - $t0" | bc)
if echo "$r" | python3 -c 'import json,sys
c=json.load(sys.stdin)["choices"][0]["message"]["content"]
assert json.loads(c)["color"] in ("red","blue")' 2>/dev/null
then pass structured "schema-valid JSON with thinking off in ${dt}s"
else fail structured "invalid or missing structured output"; fi

# 3. Embedder on disk and vector length
models=$(curl -s -m 10 "${BOX_OLLAMA_URL:-http://127.0.0.1:11434}/api/tags" | python3 -c 'import json,sys
print(" ".join(m["name"] for m in json.load(sys.stdin)["models"]))' 2>/dev/null)
emb=$(echo "$models" | tr ' ' '\n' | grep -iE 'bge|embed|minilm|e5' | head -1)
if [ -n "$emb" ]; then
  n=$(curl -s -m 60 "$EMBED_BASE_URL/embeddings" -d "{\"model\":\"$emb\",\"input\":\"hello\"}" |
    python3 -c 'import json,sys
print(len(json.load(sys.stdin)["data"][0]["embedding"]))' 2>/dev/null)
  if [ -n "$n" ]; then pass embedder "$emb returns vectors of length $n (set EMBED_DIM=$n)"
  else fail embedder "$emb is on disk but /embeddings failed"; fi
else
  warn embedder "none on disk (have: $models). DECISION: full-text fallback, EMBED_BASE_URL empty"
fi

# 4. Free memory with model loaded
avail=$(free -g | awk '/^Mem:/{print $7}')
if [ "${avail:-0}" -ge 16 ]; then pass memory "${avail} GB available (need 16)"
else fail memory "${avail} GB available, need 16"; fi

# 5. pgvector image starts
if docker info >/dev/null 2>&1; then
  img=$(grep -E 'image:.*pgvector' docker-compose.yml | head -1 | awk '{print $2}')
  if docker image inspect "${img:-pgvector/pgvector:pg16}" >/dev/null 2>&1; then
    pass pgvector "image ${img} present"
  else warn pgvector "image ${img:-pgvector} not pulled; run make db-up (needs network)"; fi
else fail pgvector "docker not reachable"; fi

# 6. Sandbox can reach the host
. box/lib.sh >/dev/null
sb="$SANDBOX"
if [ -z "$sb" ]; then warn sandbox-host "no sandbox yet (nemoclaw onboard pending)"
else
  c=$(timeout 60 nemoclaw "$sb" exec --no-tty -- \
    curl -s -m 5 -o /dev/null -w '%{http_code}' \
    "http://host.openshell.internal:11435/v1/models" 2>/dev/null)
  if [[ "$c" =~ ^(2|401) ]]; then pass sandbox-host "reached host model proxy (HTTP $c)"
  elif [ "$c" = 403 ]; then warn sandbox-host "proxy reached, call refused by policy (HTTP 403)"
  else fail sandbox-host "sandbox $sb cannot reach host.openshell.internal"; fi
fi

# 7. Concurrency decision (Ollama parallel slots; the Serve API caps with MODEL_MAX_INFLIGHT)
slots=$(curl -s -m 5 "http://127.0.0.1:${BOX_MODEL_PORT:-11436}/props" | python3 -c 'import json,sys
print(json.load(sys.stdin).get("total_slots",""))' 2>/dev/null)
inflight="MODEL_MAX_INFLIGHT=${MODEL_MAX_INFLIGHT:-4}"
if [ -n "$slots" ]; then pass concurrency "llama-server slots=$slots; $inflight"
else warn concurrency "box/model.sh not running; Ollama serves one at a time; $inflight"; fi

echo "---"; [ "$FAILS" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "$FAILS check(s) FAILED"
exit $((FAILS > 0))
