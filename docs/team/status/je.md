# Status: `je`

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

**Read this first.** wp1 to wp6 are built and green on this branch (15:15 ET). They are not on
`main` yet because the laptop has no `gh` login, so no PR could be opened. Je: please run
`gh auth login` on the laptop; the PR and merge take one minute after that. Until then nico
and blake cannot call this API from `main`. The same commits are on the remote branch
`je/wp4-owner-actions` (wp1 to wp4) and `je/wp5-topics-gaps` (wp1 to wp6).

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Skeleton and tiers | built, unmerged | none yet (no `gh` login) | `cd services/owner && uv run pytest tests/test_tiers.py tests/test_auth.py` -> 30 tier cells (10 rows x 3 modes) plus auth: agent token refused (403) on approve, reject, revert, verify and the inbox |
| wp2 Read endpoints | built, unmerged | none yet | `uv run pytest tests/test_read_endpoints.py` -> 14 passed: a Customer node and a Goal are never returned to the agent token (search by text, by label, via edges) |
| wp3 Change engine | built, unmerged | none yet | `uv run pytest tests/test_change_engine.py tests/test_agent_client_shapes.py` -> SCHEMA 10 "Agent tags a dish" and "Agent tries the locked tier" plus all ten actions and nico's gift-card plan |
| wp4 Owner-only actions and inbox | built, unmerged | none yet | `uv run pytest tests/test_owner_actions.py tests/test_inbox.py` -> "Agent adds a node type", "Agent adds an element", "Agent edits a dish" (approve, then revert restores the old text), verify gives the badge, inbox HTML and JSON |
| wp5 Topics, gaps, the owner's words | built, unmerged | none yet | `uv run pytest tests/test_gap_loop.py` -> "Gap loop" up to publish; topics never contain raw visitor text (canary test) |
| wp6 Demo seeding | built, unmerged | none yet | `uv run pytest tests/test_demo_seed.py` -> seeding makes `/owner/gaps` and `/owner/topics` show parking (5) and gift cards (12) |
| Integration on Blake's real seed | green | none yet | `uv run pytest tests/test_real_seed.py` -> 7 passed on the real Kenmore seed and registry from `scripts/seed.py` |

Whole lane: `cd services/owner && uv run pytest` -> 156 passed (about 40 s). Lint with the repo
limits (100 columns, complexity 8, 5 parameters): `uvx ruff check --line-length 100 app tests` clean.
Run the service: `cd services/owner && uv run python -m app.main` (port `OWNER_PORT`, default 8081).
Seed the demo traffic: `uv run python -m app.demo.seed_traffic` (`--reset` removes it).

## What other lanes can rely on

- `GET /openapi.json` is the live contract. Both tokens are `Authorization: Bearer`.
- `POST /owner/changes` (agent token only) answers `{ change_id, tier, state }`, plus
  `graph_version` and `prewarm` when it published. A locked change answers HTTP 403 with
  `{ change_id, tier: "locked", state: "rejected", reason }` and is recorded.
- `GET /owner/topics`, `GET /owner/gaps?state=`, `POST /owner/gaps/{id}/asked`,
  `POST /owner/answers`, `POST /owner/special-hours`, `POST /owner/publish` work as in
  SCHEMA 8.6 with the agent token (the owner token also works on these).
- Every call that publishes (`/owner/publish`, approve, revert, verify, an auto change) commits first and
  then replays the top 20 logged intents and `demo/kenmore/intents.yaml` through
  `$SERVE_BASE_URL/v1/intent` with `X-CAC-Channel: prewarm`, in the background. If the Serve API
  is down the publish still succeeds and the response says `prewarm.skipped`.
- Inbox: `GET /owner/inbox?token=$OWNER_INBOX_TOKEN` sets an HttpOnly cookie and redirects;
  `GET /owner/inbox.json` with the bearer token returns the same data.

## Measured numbers

- Lane test suite: 156 tests, about 40 s, against an embedded Postgres 16 with pgvector.
- No latency numbers yet: the Owner API has not run against the box.

## Decisions

- 15:00 Tests run against a real embedded Postgres 16 + pgvector (`pgserver`, a dev
  dependency) that loads `db/schema.sql` verbatim, because this laptop has no Docker. Same DDL,
  roles and grants; no mocks. `tests/test_real_seed.py` also runs on Blake's real seed.
- 15:00 `cac_common` is used directly; the shim was deleted once it landed on `main`.
- 15:05 Pending semantics. A new thing (label, edge type, node, edge, element) that needs a tap
  is written as a `draft` row and flipped to `approved` on approve (retired on reject). A change to
  something already published (edit, retire, add a prop) is not written until approve, so a pending
  edit never touches the published copy. `before` is captured at submit for display and again at
  approve.
- 15:05 Request shapes. The agent client (`agent/cac_owner.py`, `agent/plans/gift_card.json`)
  posts `target` as an object, `evidence` as a string, node props flat inside `after`, and form
  `fields` as names. The API accepts both these and the SCHEMA shapes and stores the SCHEMA
  shapes. A component target `{component, base}` becomes `ui_<snake_case>`.
- 15:05 Every element is stored with every catalog key, `null` when unused, plus `submit_label`
  (SCHEMA 5 note), and `selectable: true`, `version: 1`, `channels: [web, mcp]` by default.
- 15:08 `POST /owner/changes` accepts the agent token only; the owner decides through the inbox.
  Approve, reject, revert and verify accept the owner token only.
- 15:08 `reject` takes an optional `{ reason }`, stored in `evidence.rejection_reason`, which
  `GET /owner/changes` shows the agent.
- 15:08 `POST /owner/verify` updates `verified_by_owner` and `verified_at` and publishes. It does
  not write a change record (`kg.change.action` has no verify value).
- 15:10 Cookie auth for the inbox page: SameSite=Strict, HttpOnly, and a cookie-authenticated write
  must carry `X-Requested-With: cac-inbox` (the page's script adds it). The token in the URL is
  swapped for the cookie and removed from the address bar. The agent token is never accepted by the
  cookie path.
- 15:10 The owner's answers and special hours are recorded as `kg.change` rows with actor `owner`,
  state `applied`, so they show in the inbox and can be reverted.
- 15:12 `/owner/topics` returns gap phrases (`kind: gap`, with an extra `state`) and, per chosen
  component, `kind: answer` rows whose `topic` is the component name. Topic phrases are
  lower-cased, stripped to letters, digits and a little punctuation, and cut to 60 characters.
- 15:12 `POST /owner/gaps/{id}/asked` answers 409 for a gap that is already `asked` as well as for a
  second gap, so the agent does not repeat the question.
- 15:12 `POST /owner/answers` and `/owner/special-hours` do not publish; the agent calls
  `/owner/publish` next, as `agent/cac_owner.py` does. Answers containing a card number (Luhn) or an
  SSN are refused with 422.
- 15:13 Bind address is `OWNER_HOST:OWNER_PORT`, default `0.0.0.0:8081`. nico: set `OWNER_HOST` to
  the interface the sandbox reaches if you want it narrower.

## Requests handled

None addressed to `je` yet.

## Blocked on

- `NEED_INPUT: please run gh auth login on this laptop, so the agent can open and merge the PR for wp1 to wp6 (AGENTS.md section 8).`
  Nothing else is blocked: wp7 (P1) starts after the 18:30 gate.
