# Status: `blake` (Blake)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Graph write side | merged | [#5](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/5) | `make db-reset seed && uv run --project tests pytest tests/graph` -> 79 passed; `make db-check` ok; `make fixtures-check` OK (14:47 ET) |
| wp2 Serve API stub and fake model | merged | [#8](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/8) | `cd services/serve && uv run pytest tests/api` -> 75 passed (every `index.json` entry returns its golden; start-up refuses a non-local `LLM_BASE_URL`); `uv run --with pytest --with jsonschema pytest tools/fake_llm` -> 48 passed (14:52 ET) |
| wp3 Pipeline, front half | merged | [#9](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/9) | `cd services/serve && uv run pytest tests/pipeline` -> 172 passed: SCHEMA 8.2 slots pinned to 2026-10-03, section 6 expansions, schema builder reproduces the 8.1 shape, 18 retrieval smoke intents (14:52 ET) |
| wp4 Pipeline, back half | merged | [#10](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/10) | `cd services/serve && uv run pytest -m intents` against `tools/fake_llm` -> 15 passed: 30 of 30 schema-valid, 30 of 30 right component, same question twice = one model call (14:54 ET). Real model on a laptop (Ollama `qwen2.5:7b`, the same server as the box): `CAC_INTENTS_REAL_MODEL=1 LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_MODEL=qwen2.5:7b uv run pytest -m intents` -> 15 passed, 28 of 30 (15:02 ET, [#13](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/13)). On the box with `qwen3.6:35b`: pending nico's deploy |
| wp5 Actions and presets | merged | [#10](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/10) | `cd services/serve && uv run pytest tests/actions tests/api` -> lead row exists (read as `cac_owner`), past date is 422, fourth lead in an hour is 429, presets bound from the graph, CTA counted (14:54 ET) |
| wp6 Safety and steer | merged | [#10](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/10) | `cd services/serve && uv run pytest tests/intents/test_section10.py tests/binder/test_binder_safety.py` -> green: unverified diet never a badge, allergen never a dish list, goal steer, generic components for an agent-created label and form (14:54 ET) |
| wp7 Privacy proofs | merged | [#10](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/10) | `uv run --project tests python scripts/canary.py` -> exit 0, 40 prompts, 47 responses, canary and goals in none; `uv run --project tests python scripts/permission_check.py` -> 5 of 5 reads denied (14:55 ET). MCP tools are probed when `MCP_BASE_URL` is set |
| wp8 End to end | Serve side merged; five of six loops pass through je's real API; the gap loop waits for je's wp5 | [#15](https://github.com/Nicola-Bini/dell-nvidia-hackathon-2026/pull/15), [#head branch "main" is the same as base branch "main", cannot create a pull request](head branch "main" is the same as base branch "main", cannot create a pull request) | `uv run --project tests pytest tests/e2e` (needs `make fake-llm serve`, and je's API on 8081 for the owner half) -> 9 passed, 1 skipped (gap loop through je's API: his wp5 routes are not built), 1 xfailed (je's API answers before it commits; request filed). Agent adds a node type, adds an element, tags a dish, edits a dish, locked tier: all pass through both services with no restart. cj's built widget is served at `/widget/` and passes a browser run of every flow (15:20 ET) |

## What other lanes can rely on now

- `make db-up seed` gives a published graph: 175 public nodes (110 MenuItem, 13 MenuSection,
  15 FAQ, 4 Service, 3 HoursSpec, 2 SpecialHours, 10 UIComponent, ...), graph version 1.
  A database created before wp1 needs `make db-reset seed` once (it adds `pg_trgm`).
- `cac_common`: `settings.get_settings()`, `graph.reindex_node(conn, node_id)`,
  `graph.publish(conn, business_id)`, `search_text.build_search_text(...)`,
  `embedding.embed(texts)` (None when `EMBED_BASE_URL` is empty).
- Root tests and scripts run in the `tests/` uv project: `uv run --project tests ...`.
- Serve API, real pipeline: `make serve` (port `SERVE_PORT`, default 8080; the box uses
  8082). `/v1/intent` runs slots, cache, retrieval, one constrained model call, the binder
  and the request log; `/v1/view/{menu,booking,catering,hours}` are bound from the graph;
  `/v1/action` validates and stores leads (`{ ok, lead_id, surface }`, 422 with field
  errors, 429 over the limit). A publish takes effect on the next request, no restart.
  Whole suite: `cd services/serve && uv run pytest` -> 343 passed.
  `/widget/`, `/embed.js` and `/site/` are served from `apps/*/dist` as soon as the
  directory exists.
- Against the real model: `CAC_INTENTS_REAL_MODEL=1 uv run pytest -m intents` uses
  `LLM_BASE_URL` and `LLM_MODEL` from the environment instead of the fake.
- `make fake-llm`: OpenAI-compatible stand-in on `127.0.0.1:8000` (`/v1/models`,
  `/v1/chat/completions`, `/stats`, `/reset`). Other port: `uv run tools/fake_llm/server.py
  --port N`.

## Measured numbers

- Real model on a laptop (Ollama `qwen2.5:7b`, 7B, far smaller than the box's 35B): 28 of 30
  intents, 30 of 30 schema-valid, every section 10 safety row green. Structured output over
  Ollama's `/v1/chat/completions` with `response_format: json_schema` is enforced. Typical
  completion 8 to 40 tokens.

- Laptop, fake model: `/v1/intent` p50 6 ms, p95 34 ms (retrieval 6 to 30 ms); presets and
  cache hits under 10 ms. Real-model numbers come from the box (nico's status file).

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
- 14:53 An answer that binds to nothing (a diet with no dishes) is served and logged as a
  gap, with the diet or section name as `gap_topic`, so the owner is asked about it.
- 14:53 Any selected `AllergenNotice` removes every `MenuList` from the surface.
- 14:53 Preset views are not written to `ops.intent_log` (they would look like topics).
- 14:53 The lead's `component` is derived from the action and form id, never taken from the
  request body. A lead's channel is `web` unless the caller is the local MCP server.
- 14:53 wp4, wp5, wp6 and wp7 ship in one pull request: their files import each other.
- 15:00 The system prompt is a first-match rule list plus ten examples (stable, so prefix
  caching still hits). Before this a 7B model answered "gap" to most questions.
- 15:00 The model call sends `stop: ["\\n\\n"]`: Ollama's grammar allows trailing
  whitespace and a small model padded every answer to `max_tokens`.
- 15:00 MenuList: named items that all fall outside the chosen diet or section are ignored
  (the diet or section list is shown) instead of binding to nothing.
- 15:04 PR #13 was merged with one failing test (a fixture-order mistake of mine hidden by a
  shell pipeline); fixed 70 seconds later in PR #14. Proof runs now use `set -o pipefail`.
- 15:06 This laptop's ports 8000 and 8080 belong to unrelated programs, so its git-ignored
  `.env` uses 8010 (fake model) and 8082 (Serve API). Nothing committed depends on that.
- 15:15 A text that only names a preset (a goal button label, a nav label, "See the menu")
  is served as that preset with no model call. Found in the browser run: the "See the
  menu" chip, which eight catalog entries suggest, returned the gap surface.
- 15:18 A configured form with no `title` and no `rail_label` is titled from its node name.
- 15:18 Integration checks run other lanes' pushed branches from throwaway git worktrees;
  nothing in their lanes is edited. Their built `dist/` folders are copied (git-ignored)
  so the local Serve API serves the real widget.
- 14:50 `X-CAC-Channel` is ignored when a forwarding header is present, so a request through
  a tunnel or proxy on the box can never pass as `mcp` or `prewarm`.
- 14:50 A database outage answers HTTP 503 `{"detail": "database unavailable"}`; an
  unpublished graph answers 503 on `/v1/bootstrap` and `/v1/intent`.

## Requests filed

- `blake-to-nico-01-serve-start` (15:08): `box/up.sh` must start `cac_serve.main:app` and
  run `make seed` first; asks for the 30-intent and canary proofs on the box.

- `blake-to-je-01-commit-before-answer` (15:20): his API answers before its transaction
  commits; default `rail_label`; what wp5's topics and pre-warm should read and send.
- `blake-to-cj-01-widget-nav` (15:20): render `bootstrap.nav`; two cosmetic points.
- `blake-to-nico-02-gift-card-plan` (15:20): `rail_label`, `required` and `options` in the
  agent's gift-card plan.

## Requests handled

- `nico-to-blake-01-serve-port` (14:48): accepted as proposed. The Serve API listens on
  `SERVE_PORT` (8080 on laptops, 8082 on the box); `.env.example`, OWNERSHIP seam 3 and
  SCHEMA section 2 say so. Box model notes (Ollama, `qwen3.6:35b`, no embedder) are in
  `.env.example` and OWNERSHIP seam 6; the model client sends `reasoning_effort: "none"`.

## Blocked on

- wp8, owner-API half: je's `/owner/topics`, `/owner/answers` and `/owner/publish` (je wp5)
  are not on `main`. je and cj have pushed branches but opened no PR; their status says
  `gh auth login` is needed. Asked Blake (NEED_INPUT, 15:08).
- 17:00 gate on the box: needs nico to deploy `main` (request above).
