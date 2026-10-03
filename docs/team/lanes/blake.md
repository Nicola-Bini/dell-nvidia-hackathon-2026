# Lane `blake`: graph, pipeline, integration

You own the critical path. Three lanes build against what you publish, so the order below
puts whatever unblocks them first. Paths: see `tools/lanes.conf`.

Read: PRD sections 5, 7, 8 (Flow 0 and Flow 1), 9, 10, 16. SCHEMA sections 1 to 6, 7
(binder-relevant parts), 8.1 to 8.5, 9, 10. `demo/kenmore/README.md` and `fixtures/README.md`.

You are on a Max plan: run up to 5 subagents at once. wp1 and wp2 touch different
directories, so start them together.

## Work packages

| # | Package | Paths | Proof (one command, passing) | Unblocks |
|---|---|---|---|---|
| wp1 | **Graph write side.** `cac_common` (settings, `reindex_node`, `publish`; OWNERSHIP seam 2). Seed loader and `make seed`: registries from SCHEMA 5 and 6, nodes and edges from `demo/kenmore/seed.yaml` then `demo-overlay.yaml` (`ref` items become a second `HAS_ITEM` edge), catalog as `UIComponent` nodes, goals and `ADVANCES` edges, canary customer, then publish. `pg_trgm` and a full-text index for the fallback | `packages/cac_common/`, `scripts/`, `db/`, `tests/graph/`, `Makefile` | `make db-reset seed && uv run pytest tests/graph`: PRD Flow 0 acceptance (at least 20 items, hours, 2 special-hours dates, 2 services, 2 goals visible publicly only as `steer` on 2 components); a private prop on a public node is absent from `kg_public`; `make db-check` | je |
| wp2 | **Serve API stub and fake model.** All SCHEMA 8.5 routes. `/v1/intent` answers the texts in `fixtures/surfaces/index.json` with their golden surfaces, anything else with the off-topic surface. Real `/v1/bootstrap`, `/v1/view/{preset}`, `/healthz`, `/v1/metrics` (shape in seam 3), static mounts, CORS, start-up refusal when the model host is not local. `tools/fake_llm` | `services/serve/`, `tools/fake_llm/` | `uv run pytest` in `services/serve`: every entry in `index.json` returns its golden surface; start-up fails with a non-local `LLM_BASE_URL` | cj, nico |
| wp3 | **Pipeline, front half.** Normalize, slots (date resolver pinned to 2026-10-03 in tests; `closes` earlier than `opens` means the next day), `retrieve()` with vector entry plus the fixed expansions and the full-text fallback, per-request JSON Schema builder (never an empty `enum`; generic components read from `kg_public` each request) | `services/serve/` | Unit tests for SCHEMA 8.2 and section 6 expansions; schema builder reproduces the 8.1 example shape | wp4 |
| wp4 | **Pipeline, back half.** One constrained model call (temperature 0, 96 tokens, thinking off, 6 s timeout, `MODEL_MAX_INFLIGHT`), validator with one retry, binder rules 1 to 10, exact cache, request log, busy fallback | `services/serve/` | `uv run pytest -m intents` over `demo/kenmore/intents.yaml`: 30 of 30 schema-valid, at least 27 of 30 right component, against `fake_llm` locally and the real model on the box; same question twice makes one model call | gate 17:00 |
| wp5 | **Actions and presets.** `/v1/action` for the three submits with validation and HTTP 422 errors, lead insert without `RETURNING`, rate limits, presets, metrics counters, CTA counting | `services/serve/` | Tests: a lead row exists (checked as `cac_owner`); past date is 422; fourth lead in an hour is refused | cj |
| wp6 | **Safety and steer.** SCHEMA section 10 rows: unverified diet, allergen never yields a safe list, goal steer, generic components for an agent-created label and form | `services/serve/`, `tests/` | Those section 10 rows as tests, all green | gate 17:00 |
| wp7 | **Privacy proofs.** Permission script for the demo, canary script over every public endpoint (40 prompts) | `scripts/`, `tests/` | `scripts/canary.py` exits 0 and the canary name is in no response | demo |
| wp8 | **End to end with the other lanes.** Gap loop and gift-card loop through je's API with no restart; pre-warm on publish; widget served at `/widget/`; then the same on the box with nico | `tests/e2e/` | `uv run pytest tests/e2e`: SCHEMA section 10 "Gap loop" and "Agent adds a node type" rows | gate 18:30 |
| wp9 | P1, only after the 18:30 gate: slot-masked cache, then JSON-LD ingest of the demo site, then refinement | `services/serve/`, `scripts/` | Tests per feature | — |

## Known data issues in `demo/kenmore/` (found while generating the fixtures)

Handle these in the package named. The data is yours to fix where a fix is simpler than code.

| Issue | Where to handle |
|---|---|
| The Beyond Meat Burger is in the seed's `unverified_diets` and the overlay's `verified_diets`: upsert one edge, verified wins | wp1 |
| Overlay `special_hours` dates are unquoted and parse as date objects: stringify | wp1 |
| Catalog entries omit keys (`preset`, `cta_label`, `primitive`, `fields`) instead of nulling them; `say` is null on four entries | wp1, wp4 |
| `ui_form_contact` has `submit_label` and no title key; there is no base `FormCard` entry, only entries with `primitive: FormCard` | wp3, wp4 |
| `binds.labels: []` on `FactCard` and `ListCard` means any label | wp4 |
| Two section names are longer than the 24-character title limit: fall back to `rail_label` or truncate | wp4 |
| 21 items have no description; one item has `available: false`, which `MenuList` cannot show | wp4 |
| Synonym clashes: "gluten" on `alg_wheat` against `diet_gluten_free`; "plant based" on two diets; `faq_catering` against `CateringQuoteForm` for "do you cater for 40?" | wp3, wp4 (tune on the 30 intents) |
| `intents.yaml` rows have no `id`, and answer rows have no `kind` | wp4 |

## Standing duties (every loop iteration)

- You are the contract owner. Handle every `docs/team/requests/*-to-blake-*` first: change
  `docs/SCHEMA.md`, `fixtures/`, `demo/kenmore/` or `cac_common`, re-run `make fixtures-check`,
  and merge that alone so the requester can rebase.
- Read all three status files. If a lane is blocked on you, that outranks your own package.
- Copy nico's measured numbers (agent turn seconds, latency at 1, 4 and 8 concurrent) into
  the PRD where it says to replace estimates.

## Gates and cut lines

- **17:00**: `/v1/intent` passes 27 of 30. If not, stop wp5 onward and put every subagent
  on the failing intents.
- **18:30**: Flow 1 and Flow 3 acceptance pass end to end. Only then wp9.
- If the model's structured output is unreliable on the box: keep the validator and one
  retry, and ask nico to switch backend (PRD cut line 6).
- 19:30: record every flow as backup with the team. 20:00: freeze.
