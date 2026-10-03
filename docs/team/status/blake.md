# Status: `blake` (Blake)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Graph write side | merged | [#5](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/5) | `make db-reset seed && uv run --project tests pytest tests/graph` -> 79 passed; `make db-check` ok; `make fixtures-check` OK (14:47 ET) |
| wp2 Serve API stub and fake model | merged | [#8](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/8) | `cd services/serve && uv run pytest tests/api` -> 75 passed (every `index.json` entry returns its golden; start-up refuses a non-local `LLM_BASE_URL`); `uv run --with pytest --with jsonschema pytest tools/fake_llm` -> 48 passed (14:52 ET) |
| wp3 Pipeline, front half | merged | [#9](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/9) | `cd services/serve && uv run pytest tests/pipeline` -> 172 passed: SCHEMA 8.2 slots pinned to 2026-10-03, section 6 expansions, schema builder reproduces the 8.1 shape, 18 retrieval smoke intents (14:52 ET) |
| wp4 Pipeline, back half | building | | |
| wp5 Actions and presets | tests written | | |
| wp6 Safety and steer | tests written | | |
| wp7 Privacy proofs | scripts written | | |
| wp8 End to end | not started | | |

## What other lanes can rely on now

- `make db-up seed` gives a published graph: 175 public nodes (110 MenuItem, 13 MenuSection,
  15 FAQ, 4 Service, 3 HoursSpec, 2 SpecialHours, 10 UIComponent, ...), graph version 1.
  A database created before wp1 needs `make db-reset seed` once (it adds `pg_trgm`).
- `cac_common`: `settings.get_settings()`, `graph.reindex_node(conn, node_id)`,
  `graph.publish(conn, business_id)`, `search_text.build_search_text(...)`,
  `embedding.embed(texts)` (None when `EMBED_BASE_URL` is empty).
- Root tests and scripts run in the `tests/` uv project: `uv run --project tests ...`.
- Serve API stub: `make serve` (port `SERVE_PORT`, default 8080; the box uses 8082). All
  SCHEMA 8.5 routes answer. `/v1/intent` returns the golden surface for the 13 texts in
  `fixtures/surfaces/index.json` and the off-topic surface otherwise; `/v1/view/{menu,
  booking,catering,hours}` return preset surfaces; `/v1/bootstrap`, `/healthz` and
  `/v1/metrics` are real; `/v1/action` accepts the three submits (no lead stored until
  wp5). `/widget/`, `/embed.js` and `/site/` are served from `apps/*/dist` as soon as the
  directory exists, with no restart.
- `make fake-llm`: OpenAI-compatible stand-in on `127.0.0.1:8000` (`/v1/models`,
  `/v1/chat/completions`, `/stats`, `/reset`). Other port: `uv run tools/fake_llm/server.py
  --port N`.

## Measured numbers

## Decisions

- 14:35 Root tests and scripts get their own uv project in `tests/` (no root workspace, per
  AGENTS.md section 4). Proof commands are `uv run --project tests pytest tests/<dir>`.
- 14:35 Business publishes two extra props, `nav` and `chips`, so `/v1/bootstrap` reads only
  `kg_public`. Theme comes from the BrandTrait nodes.
- 14:35 `pg_trgm` and the search indexes live in `db/search.sql` (run by
  `db/init/02-search.sh`); `db/schema.sql` stays the SCHEMA section 4 DDL verbatim.
- 14:36 Configured forms (`primitive: FormCard`) may be retrieval entry nodes, and slots add
  entries (date/time -> hours, party size -> reservations, headcount -> catering). Written
  into SCHEMA section 6.
- 14:36 The Serve API loads the whole published graph into memory once per request inside
  its REPEATABLE READ transaction; retrieval, schema building and binding share that
  snapshot. Nothing is cached between requests.
- 14:40 `/v1/action` returns `lead_id` with a stored lead and HTTP 429 over the rate limit;
  card numbers and SSNs are rejected, never stored. `CAC_TODAY` pins the date for tests.
- 14:45 Imports do not rely on editable-install `.pth` files (hidden-flag problem on macOS
  under `~/Desktop`): pytest `pythonpath` and a `sys.path` line in scripts.
- 14:46 Seed re-runs upsert and never delete; an owner verification survives a re-run.
- 14:50 `fixtures/surfaces/gift_cards.json`: the FormCard `text` was hand-written prose no
  template can produce; it is now the template output ("Request a gift card: Your name,
  Email or phone, Amount."). Only the assistant-facing `text` changed, not `data`.
- 14:52 Retrieval fallback scoring and the hours-word entries are written into SCHEMA
  section 6. `ListCard.label` never offers `Service` (matches the 8.1 example).
- 14:52 Slots: a count over 20 is a headcount even after "table for"; `N/N` is month/day.
- 14:50 `X-CAC-Channel` is ignored when a forwarding header is present, so a request through
  a tunnel or proxy on the box can never pass as `mcp` or `prewarm`.
- 14:50 A database outage answers HTTP 503 `{"detail": "database unavailable"}`; an
  unpublished graph answers 503 on `/v1/bootstrap` and `/v1/intent`.

## Requests handled

- `nico-to-blake-01-serve-port` (14:48): accepted as proposed. The Serve API listens on
  `SERVE_PORT` (8080 on laptops, 8082 on the box); `.env.example`, OWNERSHIP seam 3 and
  SCHEMA section 2 say so. Box model notes (Ollama, `qwen3.6:35b`, no embedder) are in
  `.env.example` and OWNERSHIP seam 6; the model client sends `reasoning_effort: "none"`.

## Blocked on

Nothing.
