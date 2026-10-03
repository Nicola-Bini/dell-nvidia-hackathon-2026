# Status: `blake` (Blake)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Graph write side | merged | PR_WP1 | `make db-reset seed && uv run --project tests pytest tests/graph` -> 79 passed; `make db-check` ok; `make fixtures-check` OK (14:47 ET) |
| wp2 Serve API stub and fake model | building | | |
| wp3 Pipeline, front half | building | | |
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

## Requests handled

None yet.

## Blocked on

Nothing.
