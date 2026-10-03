# CAC: Chats, Agents, Context

A local agent a small business owns. It turns the business's website into a knowledge
graph and serves it as interface to visitors and as tools to AI assistants, from one Dell
Pro Max with GB10. Built at the Dell x NVIDIA AI Hackathon, Boston, 3 October 2026.

- Product: [docs/PRD.md](docs/PRD.md)
- Contracts: [docs/SCHEMA.md](docs/SCHEMA.md)
- Rules for coding agents: [AGENTS.md](AGENTS.md)
- Who owns what: [docs/team/OWNERSHIP.md](docs/team/OWNERSHIP.md)

## Start building

Each person pastes their start prompt into their coding agent. The prompt clones the repo
if needed, sets it up, and builds that person's lane.

| Person | Lane | Prompt | Work packages |
|---|---|---|---|
| Blake | Graph, pipeline, integration | [prompts/blake.md](docs/team/prompts/blake.md) | [lanes/blake.md](docs/team/lanes/blake.md) |
| Je | Owner tools API and inbox | [prompts/je.md](docs/team/prompts/je.md) | [lanes/je.md](docs/team/lanes/je.md) |
| CJ | Widget, demo site, overlay | [prompts/cj.md](docs/team/prompts/cj.md) | [lanes/cj.md](docs/team/lanes/cj.md) |
| Nico | The box, the agent, MCP | [prompts/nico.md](docs/team/prompts/nico.md) | [lanes/nico.md](docs/team/lanes/nico.md) |

## By hand

```bash
make hooks env        # lane guard on push; .env from .env.example
make db-up db-check   # Postgres + pgvector on 127.0.0.1:54320; privacy check
make fixtures-check   # seed and golden fixtures agree
```

Needs Docker, `uv`, Node 22 and the GitHub CLI.

## Layout

```
db/                 schema.sql (SCHEMA section 4) and the container init script
demo/kenmore/       the seed: The Kenmore's site facts, demo overlay, 30 intents
fixtures/           one golden surface per case
packages/cac_common shared Python (settings, search text, embedding, publish)
services/serve      Serve API, port 8080, role cac_serve
services/owner      Owner tools API and inbox, port 8081, role cac_owner
services/mcp        MCP server, port 8090 (P1)
apps/widget         the panel, embed.js, overlay
apps/demo-site      static demo site built from the seed
agent/  box/  bench/  the NemoClaw agent, box scripts, benchmarks
tools/              lane-check, fake_llm
docs/team/          ownership, lane plans, start prompts, status, requests
```
