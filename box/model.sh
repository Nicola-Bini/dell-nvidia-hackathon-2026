#!/usr/bin/env bash
# Serves qwen3.6:35b for the Serve API with llama-server on :11436, from Ollama's own
# binary and model blob. Why not Ollama itself: Ollama 0.35.1 runs this model with flash
# attention and 1024 batches, and its CUDA MUL_MAT crashes with an illegal memory access
# about one request in four (16 crashes in an hour; each costs an 8 s reload). With flash
# attention off and 512 batches: 0 crashes in 120 requests. 4 slots = 4 parallel calls.
set -u
PORT="${BOX_MODEL_PORT:-11436}"
MODELS="${OLLAMA_MODELS:-$HOME/ollama-models}"
LIB=/usr/local/lib/ollama
manifest="$MODELS/manifests/registry.ollama.ai/library/qwen3.6/35b"
blob=$(python3 -c 'import json,sys;m=json.load(open(sys.argv[1]))
d=next(l["digest"] for l in m["layers"] if l["mediaType"].endswith("model"))
print(d.replace(":","-"))' "$manifest")
if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; then echo "model up on :$PORT"; exit 0; fi
GGML_BACKEND_PATH="$LIB/cuda_v13/libggml-cuda.so" LD_LIBRARY_PATH="$LIB/cuda_v13:$LIB" \
  setsid nohup "$LIB/llama-server" --model "$MODELS/blobs/$blob" --alias qwen3.6:35b \
  --host 0.0.0.0 --port "$PORT" --no-webui --offline -ngl 99 -np "${BOX_MODEL_SLOTS:-4}" \
  -c "${BOX_MODEL_CTX:-32768}" --no-jinja --chat-template chatml --flash-attn off -b 512 -ub 512 \
  >"${CAC_LOGDIR:-$HOME/.cache/cac}/llama-server.log" 2>&1 </dev/null &
for _ in $(seq 120); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && exit 0; sleep 1; done
echo "llama-server did not become healthy; see ~/.cache/cac/llama-server.log" >&2; exit 1
