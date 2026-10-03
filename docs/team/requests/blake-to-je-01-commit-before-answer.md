# Request: blake to je: commit before the response, and three small things

Found by running your branch `je/wp4-owner-actions` (commit d67a0f2) against the real Serve
API: `tests/e2e/test_e2e_owner_api.py` on `main`. Five of the six SCHEMA section 10 loops
pass through both services with no restart. Nothing below blocks them; item 1 is a real bug.

**1. The API answers before its transaction commits.** `app/infra/db.py::get_conn` commits
when the dependency exits, and FastAPI runs that exit after the response is sent. Measured:
in 13 of 20 calls the `kg.change` row was not visible when the response arrived (0.6 to
33 ms late). Seen in practice: `create_edge` answered `graph_version: 37` while the Serve
API still served 36; a `create_node` straight after `create_label` can get 422 "unknown
label"; a pre-warm after publish would warm the old version.
**Proposal.** Commit explicitly before returning (in `_run` or each route), or open the
connection with `Depends(get_conn, scope="function")`. The test
`test_a_write_is_committed_when_the_api_answers` is a strict xfail today and will flip to
XPASS when this is fixed: tell me and I remove the marker.

**2. `create_component` without `rail_label`.** The agent's plan (`agent/plans/gift_card.json`)
creates `ui_gift_card_request` with `rail_label: null`, and `CATALOG_KEYS` drops `title`.
The Serve API now titles such a form from the node name, but a real label is better.
**Proposal.** In `catalog_entry`, default `rail_label` to the request's `title` or `name`.

**3. wp5 routes** (`/owner/topics`, `/owner/gaps`, `/owner/gaps/{id}/asked`,
`/owner/answers`, `/owner/special-hours`, `/owner/publish`) are what the "Gap loop" test and
my wp8 wait for. Pre-warm: `POST $SERVE_BASE_URL/v1/intent` with `X-CAC-Channel: prewarm`
from loopback, body `{ "text", "session_id": "prewarm" }`; on the box `SERVE_BASE_URL` is
`http://127.0.0.1:8082`. Topics: read `kind`, `gap_topic` and `selection` from
`ops.intent_log`; ignore rows with `channel = 'prewarm'` or `kind IN ('preset', 'error')`.
An answer that bound to nothing (for example a diet with no dishes) is logged as `gap` with
the diet or section name as `gap_topic`.

**4. Status file.** `docs/team/status/je.md` on your branch says wp2 to wp4 are not started.

**By.** Item 1 before the 17:00 gate; item 3 is your wp5.
