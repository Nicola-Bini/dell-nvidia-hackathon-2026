# Lane `je`: Owner tools API and owner inbox

You build the write side the always-on agent and the owner use: every change to the graph
goes through your API as a recorded, reversible change record with an approval tier.
Paths: `services/owner/` only.

Read: PRD sections 5 (principles 6 and 7), 8 (Flow 3), 9 (rows A1 to A4, O4), 10.
SCHEMA sections 1, 2, 4 (tables `kg.label`, `kg.edge_type`, `kg.node`, `kg.edge`,
`kg.change`, `ops.*`), 5, 6, 8.6, and the section 10 rows that start with "Agent" or "Gap".
OWNERSHIP seams 1, 2 and 5.

You are on a Pro plan: at most 2 subagents at a time, on `sonnet`, and only for packages
that split into separate files (for example wp2's read endpoints while you do wp3).

## Work packages

| # | Package | Proof (one command, passing) | Unblocks |
|---|---|---|---|
| wp1 | **Skeleton and tiers.** FastAPI on 8081, role `cac_owner`, `/healthz`. Two credentials: `OWNER_TOOLS_TOKEN` (agent) and `OWNER_INBOX_TOKEN` (owner). Tier assignment as a pure function of (action, target, current state, `CAC_AUTONOMY`) covering every row of the SCHEMA 8.6 tier table | `uv run pytest` in `services/owner`: one test per tier-table cell; agent token refused on an owner-only route | nico |
| wp2 | **Read endpoints.** `/owner/schema`, `/owner/graph/search`, `/owner/changes`, `/owner/digest`. Locked labels by name only; never lead payloads or visitor text | Tests: a Customer node and a Goal are never returned to the agent token | nico |
| wp3 | **Change engine.** `POST /owner/changes` for all ten actions: apply to `kg`, store `before` and `after`, force `source_type = agent` and `verified_by_owner = false`, call `reindex_node`, refuse the locked tier with a reason, publish when the tier is `auto` | Tests: SCHEMA section 10 "Agent tags a dish" and "Agent tries the locked tier" | gate 17:00 |
| wp4 | **Owner-only actions and inbox.** `approve`, `reject`, `revert`, `/owner/verify`. `GET /owner/inbox` as an HTML page (pending changes with reason and evidence, unverified tags with confirm, applied changes with revert, new leads, open gaps) and `/owner/inbox.json` | Tests: section 10 "Agent adds a node type", "Agent adds an element", "Agent edits a dish" (approve, then revert restores the old text) | gate 17:00 |
| wp5 | **Topics, gaps, the owner's words.** `/owner/topics` (fold new `ops.intent_log` rows using `ops.sync_state`, create or update `KnowledgeGap` nodes), `/owner/gaps`, `/owner/gaps/{id}/asked` (one `asked` at a time), `/owner/answers`, `/owner/special-hours`, `/owner/publish` with pre-warm (seam 5) | Tests: section 10 "Gap loop" up to publish; topics never contain raw visitor text | nico, blake wp8 |
| wp6 | **Demo seeding.** A script that inserts the pre-demo traffic: 5 sessions asking about parking (a real gap in the Kenmore data; it stands in for the PRD's gluten-free pasta) and 12 about gift cards (PRD section 15) | Running it makes `/owner/gaps` and `/owner/topics` show both topics | demo |
| wp7 | P1, only after the 18:30 gate: digest wording, owner-initiated facts | Tests per feature | — |

## Working before the other lanes land

- Until blake's wp1 merges there is no seed and no `cac_common`. Start wp1 (pure logic and
  auth need neither), and for wp2 onward use a small fixture graph your tests insert
  themselves, plus `services/owner/app/infra/common_shim.py` implementing the three
  `cac_common` calls from seam 2. Delete the shim when the package is on `origin/main`.
- Pre-warm calls the Serve API. If it is down, publish still succeeds and logs the skip.
- nico's agent is your main consumer. Keep `/openapi.json` accurate, and when you change a
  request or response shape say so in your status file under "Decisions".

## Gates and cut lines

- **17:00**: wp1 to wp4 merged; nico's agent can create a gift-card type and leave it
  pending, and the inbox can approve it.
- **18:30**: wp5 merged; the gap loop works end to end with blake's Serve API.
- If you are behind at 17:00: ship the inbox as JSON plus the plainest HTML table with
  buttons, and drop `reject` reasons, digest polish and wp6's script (seed those rows by
  SQL instead).
