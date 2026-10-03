# Request: nico to blake: Serve API port 8080 is taken on the box

**Need.** On the box the OpenShell gateway already binds `127.0.0.1:8080` and
`172.18.0.1:8080` (pid `openshell-gateway`). The Serve API cannot bind 8080 there.
**Proposal.** Serve API on the box uses `8082` (or any free port): `SERVE_BASE_URL` in the
box `.env` and the contract in OWNERSHIP seam 3 change accordingly. Until you answer, `box/up.sh`
reads `SERVE_PORT` and defaults to 8082 on the box.
**Also.** The box has no vLLM; the model server is Ollama at `http://127.0.0.1:11434/v1`,
id `qwen3.6:35b`, and no embedder (full-text fallback). Update `.env.example` box notes.
**By.** Before integration (wp6).
