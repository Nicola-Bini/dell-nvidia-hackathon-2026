# CAC MCP server (Flow 2, P1)

Stateless Streamable HTTP at `POST /mcp` (SCHEMA 8.7). It holds no database credentials:
every tool is a call to the Serve API on this machine with `X-CAC-Channel: mcp`. Questions
and lead payloads are never logged; the log has one line per call (tool, outcome, ms).

```bash
npm ci
npm test                 # 10 tests against a fake Serve API that answers with fixtures/
npm run typecheck
SERVE_BASE_URL=http://127.0.0.1:8082 npm start      # box/up.sh does this
```

| Variable | Default | Meaning |
|---|---|---|
| `SERVE_BASE_URL` | `http://127.0.0.1:8080` | The Serve API; loopback or it will not start |
| `MCP_PORT`, `MCP_HOST` | `8090`, `127.0.0.1` | Where it listens (the tunnel is local) |
| `MCP_ALLOWED_HOSTS` | empty | The tunnel hostname(s), comma-separated. Any other Host gets 403 |
| `MCP_SURFACE_HTML` | `apps/widget/dist-mcp/surface.html` | The widget as one HTML file |

Tools: `get_business_profile`, `ask_restaurant`, `get_view`, `request_booking`,
`request_catering_quote`. `ask_restaurant` and `get_view` return the views' text as
`content` and the Surface (SCHEMA 8.4) as `structuredContent`. The two request tools return
`{ ok, lead_id, surface }`; a refusal is `isError` with one `field: message` line per error.

**Element.** While `MCP_SURFACE_HTML` does not exist the server is text-only. Once cj's
`npm run build:mcp` writes it, `ask_restaurant` declares `ui://cac/surface.html` and
`get_view` becomes app-only, with no restart: the file is read on each request.

**Tunnel and connector (a person).** Only `/mcp` answers a public Host; `/health` is local.

```bash
cloudflared tunnel --url http://127.0.0.1:8090        # prints https://<name>.trycloudflare.com
# put <name>.trycloudflare.com in .env as MCP_ALLOWED_HOSTS, restart the MCP server, then in
# Claude: Settings, Connectors, Add custom connector, URL https://<name>.trycloudflare.com/mcp
MCP_BASE_URL=http://127.0.0.1:8090 uv run --project tests python scripts/canary.py
```
