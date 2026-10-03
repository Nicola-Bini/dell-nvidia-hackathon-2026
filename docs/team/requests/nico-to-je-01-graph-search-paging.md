# Request: nico to je: page through `GET /owner/graph/search`

**Need.** The agent's `grow` move reads every node of a type to tag and link them.
`/owner/graph/search` returns at most 25 nodes, ordered by id, with no way to get the rest
(`reads.search_nodes(..., limit=25)`). The Kenmore menu alone has more than 25 MenuItems.
**Proposal.** Two optional query parameters, nothing else changes:
`GET /owner/graph/search?q=&label=&limit=<1..200, default 25>&after=<node id>` returning
nodes with `id > after` in id order. Same locked-label rules.
**Until then.** `agent/cac_grow.py:nodes_of` splits a full page by id prefix (`q=mi_a`,
`q=mi_b`, ...) and unions the pages. It works, at about 40 small requests per large type
per heartbeat.
**By.** Not blocking; after the 18:30 gate is fine.
