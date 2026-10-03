# Status: `je` (Je)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Skeleton and tiers | built, awaiting PR | pending | `uv run pytest` in `services/owner` -> 48 passed (30 tier cells, auth) |
| wp2 Read endpoints | not started | | |
| wp3 Change engine | not started | | |
| wp4 Owner-only actions and inbox | not started | | |
| wp5 Topics, gaps, the owner's words | not started | | |
| wp6 Demo seeding | not started | | |

## Measured numbers

## Decisions

- Tests run against a real embedded Postgres 16 + pgvector (`pgserver`, a dev dependency) that
  loads `db/schema.sql` verbatim, because this laptop has no Docker. Same DDL, no mocks.
- The tier function takes a `TargetState` read from `kg` by the caller, so it stays pure.
- `app/infra/common_shim.py` stands in for `cac_common` (seam 2) until it lands on main.
- Inbox page accepts the owner token as `Authorization: Bearer`, `?token=` or a cookie, since
  a browser cannot set headers on a page load.

## Requests handled

## Blocked on

- `gh auth login` is needed to open and merge PRs (AGENTS.md section 8).
