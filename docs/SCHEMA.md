# CAC — Schema and Contracts

Companion to [PRD.md](PRD.md). This file is the source of truth for scaffolding: runtime
processes, the graph store, the label and edge registries, the UI component catalog, and the
wire contracts between the model, the Serve API, the widget, the agent, and external assistants.

Version 2, 3 October 2026. Revised after an independent review that ran the DDL in a test
database and checked the contracts against the PRD's acceptance criteria.

## 1. Design rules

1. **Default private.** A node is private and draft until someone marks it public and the owner
   approves it. Nothing reaches a visitor or an assistant before `kg.publish()` copies it.
2. **The partition is enforced by the database, not the prompt.** The Serve API connects as
   `cac_serve`, which has no grant on the `kg` schema. It can only read `kg_public`.
3. **Publish copies an allowlist.** Only props named in the label registry cross the boundary.
   A private prop left on a public node (supplier, margin) is dropped at publish.
4. **The model chooses, code writes.** The model returns a component name and ids from a list
   it was given. Every word and number a visitor sees comes from the graph or from a template.
   The model writes no visitor-facing text.
5. **No model-written queries.** Retrieval is vector entry plus fixed expansion templates.
6. **Anonymous text never drives an agent that holds tools.** Visitors get one tool-less
   constrained completion. The agent that can write to the graph sees only a short topic and
   a count, and can only write the owner's own words.
7. **Provenance on everything.** Every node and edge records its source and whether the owner
   verified it.
8. **One business per box in v0.** Every process reads `CAC_BUSINESS_ID`. Requests never carry
   a business id. The `business_id` columns are for later; a second business needs its own
   database and roles.

## 2. Runtime

| Process | Stack | Port | Database role | Reachable from |
|---|---|---|---|---|
| Serve API | Python 3.12, FastAPI, psycopg 3 with raw SQL (no ORM) | 8080 | `cac_serve` | Site visitors; MCP server on localhost |
| Owner tools API | Python, FastAPI | 8081 | `cac_owner` | The sandboxed agent and the owner's browser on the local network. Never tunnelled |
| MCP server | Node 22, from Anthropic's MCP Apps quickstart | 8090 | none (calls Serve API) | The tunnel: only `/mcp` |
| Widget | Vite, React, TypeScript; served by the Serve API at `/widget/` | — | — | Browser iframe; also built as one HTML file for the MCP App |
| Postgres + pgvector | Docker | 127.0.0.1:5432 | — | Local processes only |
| Model server | vLLM managed by NemoClaw (OpenAI-compatible) | 8000 | — | Serve API and NemoClaw |
| Embedder | Local embedding model (decided in the first-30-minute checks) | — | — | Serve API, Owner tools API |
| Agent | OpenClaw agent in a NemoClaw / OpenShell sandbox | — | none (calls Owner tools API) | Owner channel |

No ORM on the Serve API: `cac_serve` can insert into the log and lead tables but not read
them, and an ORM's `RETURNING` clause fails without read permission.

Environment:

| Variable | Meaning |
|---|---|
| `CAC_BUSINESS_ID` | `biz_demo` |
| `CAC_TZ` | Business timezone, `America/New_York` |
| `SERVE_DATABASE_URL`, `OWNER_DATABASE_URL` | Connection strings for the two roles |
| `LLM_BASE_URL`, `LLM_MODEL` | Local model endpoint. The Serve API refuses to start unless the host is loopback or the box's own address |
| `EMBED_BASE_URL`, `EMBED_MODEL`, `EMBED_DIM` | Local embedder; same start-up check |
| `OWNER_TOOLS_TOKEN` | Bearer token the agent sends to the Owner tools API |
| `OWNER_CHANNEL_USER_ID` | The one identity allowed to speak as the owner on the owner channel |
| `MODEL_MAX_INFLIGHT` | Cap on concurrent model calls from the Serve API |
| `INTENT_MAX_CHARS` | 300 |
| `CAC_ALLOWED_ORIGINS` | Origins allowed to embed the widget |
| `GAP_ASK_MIN_SESSIONS` | Distinct sessions before a gap is put to the owner (1 for the demo, 3 normally) |

Start order, each gated on a health check: Postgres, embedder, Owner tools API, Serve API,
MCP server, tunnel. A recovery script restarts Docker, the OpenShell gateway, and the NemoClaw
sandbox, then re-runs the start order (NemoClaw does not restart on its own after a reboot).

## 3. Storage layout

One Postgres container with pgvector. Image `pgvector/pgvector:pg18-trixie` exists for arm64;
the DDL below was run on `pg16`, so either works. For pg18 images mount the data volume at
`/var/lib/postgresql`, not `/var/lib/postgresql/data`.

| Schema | Contents | `cac_owner` | `cac_serve` |
|---|---|---|---|
| `kg` | Full graph: public, private, drafts, goals, gaps | read/write | no access |
| `kg_public` | Published projection: approved public nodes, allowlisted props | written by `publish()` | read only |
| `ops` | Intent log, cache, leads | read/write | insert-only on log and leads; read/write cache |

The image's default `postgres` user is a superuser and bypasses all of this. Use it once for
bootstrap and never from an application.

## 4. DDL

Before running: confirm the embedding model on the box, record its vector length, and replace
`1024` below if it differs (`bge-m3` and `qwen3-embedding:0.6b` are 1024; `nomic-embed-text`
is 768).

```sql
-- Run once as the bootstrap superuser, with psql:
--   psql -v owner_pw="$CAC_OWNER_PASSWORD" -v serve_pw="$CAC_SERVE_PASSWORD" -f schema.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE cac_owner LOGIN PASSWORD :'owner_pw';
CREATE ROLE cac_serve LOGIN PASSWORD :'serve_pw';

CREATE SCHEMA kg AUTHORIZATION cac_owner;
CREATE SCHEMA kg_public AUTHORIZATION cac_owner;
CREATE SCHEMA ops AUTHORIZATION cac_owner;

SET ROLE cac_owner;

-- 4.1 Label registry: which labels may be published, and which of their props
CREATE TABLE kg.label (
  label          text PRIMARY KEY,
  may_be_public  boolean NOT NULL,
  public_props   text[] NOT NULL DEFAULT '{}',
  description    text NOT NULL
);

-- 4.2 Full graph
CREATE TABLE kg.node (
  id                 text PRIMARY KEY,            -- prefixed slug, e.g. mi_mushroom_risotto
  business_id        text NOT NULL,
  label              text NOT NULL REFERENCES kg.label(label),
  name               text NOT NULL,
  props              jsonb NOT NULL DEFAULT '{}'::jsonb,
  visibility         text NOT NULL DEFAULT 'private'
                     CHECK (visibility IN ('public', 'private')),
  status             text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'approved', 'retired')),
  source_type        text NOT NULL
                     CHECK (source_type IN ('jsonld', 'html', 'pdf', 'image', 'owner', 'agent', 'seed')),
  source_url         text,
  extracted_by       text,                        -- model id or person
  verified_by_owner  boolean NOT NULL DEFAULT false,
  verified_at        timestamptz,
  search_text        text NOT NULL DEFAULT '',    -- built from name and public props only
  embedding          vector(1024),
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX node_business_label_idx ON kg.node (business_id, label);

CREATE TABLE kg.edge (
  id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  business_id        text NOT NULL,
  src                text NOT NULL REFERENCES kg.node(id) ON DELETE CASCADE,
  dst                text NOT NULL REFERENCES kg.node(id) ON DELETE CASCADE,
  type               text NOT NULL,               -- see edge registry
  props              jsonb NOT NULL DEFAULT '{}'::jsonb,
  status             text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'approved', 'retired')),
  source_type        text NOT NULL
                     CHECK (source_type IN ('jsonld', 'html', 'pdf', 'image', 'owner', 'agent', 'seed')),
  verified_by_owner  boolean NOT NULL DEFAULT false,
  verified_at        timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (src, dst, type)
);
CREATE INDEX edge_src_idx ON kg.edge (src, type);
CREATE INDEX edge_dst_idx ON kg.edge (dst, type);

-- 4.3 Published projection: the only graph the serving role can read
CREATE TABLE kg_public.node (
  id                 text PRIMARY KEY,
  business_id        text NOT NULL,
  label              text NOT NULL,
  name               text NOT NULL,
  props              jsonb NOT NULL,
  verified_by_owner  boolean NOT NULL,
  verified_at        timestamptz,
  search_text        text NOT NULL,
  embedding          vector(1024)
);
CREATE INDEX public_node_label_idx ON kg_public.node (business_id, label);
CREATE INDEX public_node_embedding_idx ON kg_public.node USING hnsw (embedding vector_cosine_ops);

CREATE TABLE kg_public.edge (
  src                text NOT NULL REFERENCES kg_public.node(id) ON DELETE CASCADE,
  dst                text NOT NULL REFERENCES kg_public.node(id) ON DELETE CASCADE,
  type               text NOT NULL,
  props              jsonb NOT NULL,
  verified_by_owner  boolean NOT NULL,
  PRIMARY KEY (src, dst, type)
);
CREATE INDEX public_edge_dst_idx ON kg_public.edge (dst, type);

CREATE TABLE kg_public.meta (
  business_id    text PRIMARY KEY,
  graph_version  integer NOT NULL,
  published_at   timestamptz NOT NULL
);

-- 4.4 Runtime tables
CREATE TABLE ops.intent_log (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ts             timestamptz NOT NULL DEFAULT now(),
  business_id    text NOT NULL,
  channel        text NOT NULL CHECK (channel IN ('web', 'nav', 'mcp', 'a2a', 'prewarm')),
  session_id     text,
  text           text NOT NULL,                  -- raw visitor text: private
  slots          jsonb NOT NULL DEFAULT '{}'::jsonb,
  cache          text NOT NULL CHECK (cache IN ('exact', 'semantic', 'miss', 'preset')),
  selection      jsonb,
  kind           text NOT NULL CHECK (kind IN ('answer', 'gap', 'off_topic', 'preset', 'error')),
  gap_topic      text,                           -- set when kind = 'gap'
  latency_ms     integer NOT NULL,
  model          text,
  graph_version  integer NOT NULL
);

CREATE TABLE ops.intent_cache (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  business_id      text NOT NULL,
  graph_version    integer NOT NULL,
  normalized_hash  text NOT NULL,                -- sha256 hex of the normalized text
  slots_key        text NOT NULL,                -- canonical string of extracted slots
  embedding        vector(1024),                 -- semantic cache (P1)
  selection        jsonb NOT NULL,               -- the model's choice only; never text or data
  hits             integer NOT NULL DEFAULT 0,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (business_id, graph_version, normalized_hash, slots_key)
);

CREATE TABLE ops.lead (
  id           uuid PRIMARY KEY,                 -- generated by the caller
  ts           timestamptz NOT NULL DEFAULT now(),
  business_id  text NOT NULL,
  kind         text NOT NULL
               CHECK (kind IN ('booking_request', 'catering_quote', 'pickup_order', 'form')),
  component    text NOT NULL,                    -- which element produced it
  payload      jsonb NOT NULL,                   -- customer details: private, on the box only
  channel      text NOT NULL CHECK (channel IN ('web', 'mcp', 'a2a')),
  session_id   text,
  status       text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'seen'))
);

CREATE TABLE ops.sync_state (
  key    text PRIMARY KEY,                       -- e.g. 'gap_watermark'
  value  bigint NOT NULL
);

-- 4.5 Publish: the owner-approved step that moves data across the boundary
CREATE FUNCTION kg.publish(p_business text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
  v_version integer;
BEGIN
  DELETE FROM kg_public.node WHERE business_id = p_business;  -- edges cascade

  INSERT INTO kg_public.node
    (id, business_id, label, name, props, verified_by_owner, verified_at, search_text, embedding)
  SELECT n.id, n.business_id, n.label, n.name,
         COALESCE((SELECT jsonb_object_agg(p.key, p.value)
                   FROM jsonb_each(n.props) AS p
                   WHERE p.key = ANY (l.public_props)), '{}'::jsonb),
         n.verified_by_owner, n.verified_at, n.search_text, n.embedding
  FROM kg.node n
  JOIN kg.label l ON l.label = n.label
  WHERE n.business_id = p_business
    AND n.visibility = 'public'
    AND n.status = 'approved'
    AND l.may_be_public;

  INSERT INTO kg_public.edge (src, dst, type, props, verified_by_owner)
  SELECT e.src, e.dst, e.type,
         COALESCE((SELECT jsonb_object_agg(p.key, p.value)
                   FROM jsonb_each(e.props) AS p
                   WHERE p.key IN ('position', 'weight')), '{}'::jsonb),
         e.verified_by_owner
  FROM kg.edge e
  WHERE e.business_id = p_business
    AND e.status = 'approved'
    AND EXISTS (SELECT 1 FROM kg_public.node s WHERE s.id = e.src)
    AND EXISTS (SELECT 1 FROM kg_public.node d WHERE d.id = e.dst);

  -- Goals stay private; components only receive a numeric steering weight (5 = most important).
  UPDATE kg_public.node c
  SET props = c.props || jsonb_build_object('steer', s.weight)
  FROM (
    SELECT e.src AS component_id,
           max(CASE WHEN g.props ->> 'priority' ~ '^[1-5]$'
                    THEN (g.props ->> 'priority')::integer END) AS weight
    FROM kg.edge e
    JOIN kg.node g ON g.id = e.dst
    WHERE e.business_id = p_business
      AND e.type = 'ADVANCES' AND e.status = 'approved'
      AND g.label = 'Goal' AND g.status = 'approved'
    GROUP BY e.src
  ) s
  WHERE c.id = s.component_id AND s.weight IS NOT NULL;

  INSERT INTO kg_public.meta (business_id, graph_version, published_at)
  VALUES (p_business, 1, now())
  ON CONFLICT (business_id) DO UPDATE
    SET graph_version = kg_public.meta.graph_version + 1, published_at = now()
  RETURNING graph_version INTO v_version;

  DELETE FROM ops.intent_cache
  WHERE business_id = p_business AND graph_version < v_version;

  RETURN v_version;
END $$;

-- 4.6 Grants: cac_serve never receives anything on schema kg
GRANT USAGE ON SCHEMA kg_public TO cac_serve;
GRANT SELECT ON ALL TABLES IN SCHEMA kg_public TO cac_serve;
GRANT USAGE ON SCHEMA ops TO cac_serve;
GRANT INSERT ON ops.intent_log, ops.lead TO cac_serve;
GRANT SELECT, INSERT, UPDATE ON ops.intent_cache TO cac_serve;

RESET ROLE;
```

`cac_serve` is insert-only on `ops.intent_log` and `ops.lead`. Use plain inserts with no
`RETURNING` and no `ON CONFLICT` (both need read permission). Treat a duplicate-key error on
`ops.lead` as "already stored".

## 5. Label registry

How the whiteboard's four graph sections map here:

| Whiteboard | In this schema |
|---|---|
| Goals | `Goal` nodes (private) |
| UI element library | `UIComponent` nodes (section 7) |
| Context library | Business through FAQ in the table below |
| Connections | `ADVANCES` (element to goal), each element's `binds` (element to the context it may show), and in P1 `RENDERS_WITH` (intent to element) |

Seed `kg.label` with these rows. `public_props` is exactly the props listed; anything else on
a node is dropped at publish. `search_text` is built only from `name` and these props.

| Label | Prefix | Public | Props | Build |
|---|---|---|---|---|
| Business | `biz_` | yes | `cuisine`, `price_range`, `phone`, `url`, `tagline`, `timezone` | P0 |
| Location | `loc_` | yes | `street`, `city`, `region`, `postal`, `maps_url`, `parking`, `transit` | P0 |
| HoursSpec | `hrs_` | yes | `days` (mon..sun), `opens`, `closes` (HH:MM) | P0 |
| SpecialHours | `sh_` | yes | `date` (YYYY-MM-DD), `closed`, `opens`, `closes`, `note` | P0 |
| MenuSection | `sec_` | yes | `position` | P0 |
| MenuItem | `mi_` | yes | `description`, `price_cents`, `currency`, `available` | P0 |
| Diet | `diet_` | yes | `schema_org`, `synonyms` | P0 |
| Allergen | `alg_` | yes | `fda_major`, `synonyms` | P0 |
| Service | `svc_` | yes | `kind` (reservations, catering, takeout, private_events), `details`, `min_headcount`, `booking_url` | P0 |
| FAQ | `faq_` | yes | `question`, `answer` | P0 |
| UIComponent | `ui_` | yes | catalog entry keys (section 7) | P0 |
| Goal | `goal_` | **no** | `statement`, `priority` (1..5, 5 = most important) | P0 |
| KnowledgeGap | `gap_` | **no** | `topic`, `count`, `sessions`, `state` (open, asked, answered), `origin` (visitor, onboarding) | P0 |
| Customer | `cust_` | **no** | `name`, `contact`, `notes` | P0 (canary only) |
| ReviewSummary | `rev_` | yes | `rating`, `count`, `source`, `highlights` | P1 |
| BrandTrait | `trait_` | yes | `kind` (color, font, tone), `value` | P1 |
| Intent | `int_` | yes | `examples`, `kind` (know, order, book, contact) | P1 |
| Ingredient | `ing_` | yes | — | later |
| MediaAsset | `img_` | yes | `url`, `alt` | later |
| Promotion | `promo_` | yes | `details`, `days` | later |
| Proposal | `prop_` | **no** | `kind`, `draft`, `reason` | P1 |
| OwnerNote | `note_` | **no** | `text` | later |

Site content that fits no typed label (about, story, policies) is stored as an FAQ with the
page heading as `question`.

`FAQ.question` is always a canonical rewrite or seed text, never copied from a visitor's
message.

## 6. Edge registry

| Type | From → To | Props | Build | Notes |
|---|---|---|---|---|
| `HAS_LOCATION` | Business → Location | — | P0 | |
| `HAS_HOURS` | Business → HoursSpec, SpecialHours | — | P0 | Open or closed is computed in code |
| `HAS_SECTION` | Business → MenuSection | — | P0 | |
| `HAS_ITEM` | MenuSection → MenuItem | `position` | P0 | |
| `SUITABLE_FOR` | MenuItem → Diet | — | P0 | Badge shown only if `verified_by_owner` |
| `CONTAINS_ALLERGEN` | MenuItem → Allergen | — | P0 | Shown as fact only if `verified_by_owner` |
| `OFFERS` | Business → Service | — | P0 | |
| `ANSWERS` | FAQ → Business, Service, MenuItem | — | P0 | |
| `ADVANCES` | UIComponent → Goal | — | P0 | Never published; becomes `steer` |
| `ABOUT` | KnowledgeGap → FAQ, SpecialHours | — | P0 | Links a gap to what answered it |
| `RENDERS_WITH` | Intent → UIComponent | `weight` | P1 | |
| `PAIRS_WITH` | MenuItem → MenuItem | — | later | |
| `CONTAINS` | MenuItem → Ingredient | — | later | |
| `DEPICTS` | MediaAsset → any public node | — | later | |

Retrieval: embed the visitor's text, take the top 8 nodes by cosine similarity among data
labels (never UIComponent), drop weak matches (threshold tuned on the fixture set, start at
0.35), expand with the fixed templates below, and cap at 40 candidates.

| Entry label | Expansion |
|---|---|
| Diet | MenuItems with an approved `SUITABLE_FOR` edge to it, and their sections |
| Allergen | MenuItems with an owner-verified `CONTAINS_ALLERGEN` edge to it |
| MenuItem | its section, diets, allergens |
| MenuSection | its items |
| Service | FAQs that `ANSWERS` it |
| HoursSpec, SpecialHours | all hours nodes |
| FAQ | the node itself |

If no embedding model is available on the box, the same `retrieve(text) → candidates` function
is backed by Postgres full-text search plus `pg_trgm` over `search_text`, using the `synonyms`
props.

## 7. UI component catalog

The catalog is the set of owner-approved `UIComponent` nodes. Each maps to one prebuilt React
component. "Element" on the whiteboard and "component" here are the same thing. The vocabulary
(catalog, surface, action) follows Google's A2UI so the format can be mapped to an A2UI catalog
later; v0 does not ship an A2UI renderer.

Catalog entry (the props of a `UIComponent` node, id `ui_<component>`):

```json
{
  "component": "BookingForm",
  "version": 1,
  "use_when": "Visitor wants a table or asks how to reserve.",
  "binds": { "labels": ["Service"], "min": 1, "max": 1 },
  "selectable": true,
  "preset": "booking",
  "cta_label": "Book a table",
  "rail_label": "Booking",
  "say": "Tell us when and how many.",
  "chips": ["See the menu", "Are you open tonight?"],
  "channels": ["web", "mcp"],
  "primitive": null,
  "fields": null
}
```

| Component | Use when | Binds | Chosen by | Actions | Build |
|---|---|---|---|---|---|
| `Answer` | An owner-written FAQ answers the question | FAQ[1] | model picks the FAQ id | — | P0 |
| `MenuList` | Dishes, diets, courses, named dishes | MenuItem[1..12] | model picks a filter; code builds the list | `add_to_cart` when the visitor wants to order | P0 |
| `HoursCard` | Opening hours, "are you open on…" | HoursSpec, SpecialHours | code, from the date slot | — | P0 |
| `BookingForm` | Wants a table | Service[reservations] | code, prefilled from slots | `submit_booking_request` | P0 |
| `CateringQuoteForm` | Catering, large groups, events | Service[catering] | code, prefilled from slots | `submit_catering_quote` | P0 |
| `AllergenNotice` | Any diet or allergen involvement; or the visitor names an allergen | Allergen[0..1] | binder inserts it; model may pick it with an allergen id | — | P0 |
| `GoalCTA` | Binder inserts it from `steer` | UIComponent | binder | `open_view:<preset>` | P0 |
| `LocationCard` | Address, directions, parking, contact | Location | code | `directions`, `call` | P1 |
| `ItemCard` | One specific dish | MenuItem[1] | model picks the id | `add_to_cart` | P1 |
| `ReviewHighlights` | Reputation | ReviewSummary | code | — | P1 |
| `Cart` | Reviewing and submitting the cart | client state | client | `submit_pickup_order` | P1 |
| `FormCard` | A generic lead form configured by `fields` (gift cards, private dining, a salon booking with a staff field) | Service[1] | model picks it | `submit_form` | P1 |

`FormCard` is how new elements get created without new code: the agent proposes an entry with
`primitive: "FormCard"` and a `fields` list (`name`, `type`, `label`, `required`); the owner
approves; after publish the model can select it.

Actions never call the model:

| Action | Handler | Effect |
|---|---|---|
| `add_to_cart` | client | Increments the cart count in the widget (P0: count only; reviewing and submitting the cart is P1) |
| `open_view:<preset>` | client → `GET /v1/view/{preset}` | Shows a preset surface |
| `submit_booking_request` | server | Inserts `ops.lead` (`booking_request`). A request, not a confirmed reservation. If the Service has `booking_url`, the form shows a link to the site's existing booking system instead |
| `submit_catering_quote` | server | Inserts `ops.lead` (`catering_quote`) |
| `submit_pickup_order`, `submit_form` | server | P1 |
| `directions`, `call` | client | P1 |

Presets are fixed surfaces served with no model call:

| Preset id | Surface | Build |
|---|---|---|
| `menu` | One `MenuList` per MenuSection (exempt from the 12-item and 2-view limits) | P0 |
| `booking` | `BookingForm` | P0 |
| `catering` | `CateringQuoteForm` | P0 |
| `hours` | `HoursCard` for this week | P0 |
| `contact` | `LocationCard` + `HoursCard` | P1 |
| `reviews` | `ReviewHighlights` | P1 |

Embed on the existing site:

```html
<div id="cac-root"></div>
<script src="https://BOX_HOST/embed.js" async></script>
```

- `embed.js` first fetches `/healthz` with a 1 s timeout. If the box is unreachable it does
  nothing, and the site behaves exactly as before.
- It injects `<iframe src="BOX_HOST/widget/" sandbox="allow-scripts allow-forms allow-same-origin">`
  into `#cac-root`. If that element is absent it adds a launcher at the bottom right.
- Existing nav links marked `data-cac-preset="menu|booking|catering|hours"` are intercepted:
  the script posts `{ "type": "cac:view", "preset": "<id>" }` to the iframe. Without the
  script the links work as normal links.
- The widget keeps `session_id` (a UUID) and the history rail in `sessionStorage`. The rail is
  client state: each entry is `{ surface_id, title, surface }`; clicking a chip re-renders the
  stored surface with no request; the newest is labelled "Current".
- Every string is rendered as text, never as HTML.

## 8. Wire contracts

### 8.1 Selection (model output)

One constrained completion per uncached intent. The Serve API builds the JSON Schema per
request from the approved catalog and the retrieved candidates, and passes it to the local
model as a structured-output constraint. The model can only name components that are approved
and ids that were retrieved.

```json
{
  "anyOf": [
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "views"],
      "properties": {
        "kind": { "const": "answer" },
        "views": {
          "type": "array", "minItems": 1, "maxItems": 2,
          "items": {
            "anyOf": [
              {
                "type": "object", "additionalProperties": false,
                "required": ["component", "diet", "section", "items", "order"],
                "properties": {
                  "component": { "const": "MenuList" },
                  "diet": { "enum": ["diet_vegetarian", "diet_vegan", null] },
                  "section": { "enum": ["sec_mains", "sec_desserts", null] },
                  "items": {
                    "type": "array", "maxItems": 6,
                    "items": { "enum": ["mi_mushroom_risotto", "mi_caprese", "mi_ribeye"] }
                  },
                  "order": { "type": "boolean" }
                }
              },
              {
                "type": "object", "additionalProperties": false,
                "required": ["component", "faq"],
                "properties": {
                  "component": { "const": "Answer" },
                  "faq": { "enum": ["faq_parking", "faq_gluten_free_pasta"] }
                }
              },
              {
                "type": "object", "additionalProperties": false,
                "required": ["component", "allergen"],
                "properties": {
                  "component": { "const": "AllergenNotice" },
                  "allergen": { "enum": ["alg_peanuts"] }
                }
              },
              {
                "type": "object", "additionalProperties": false,
                "required": ["component"],
                "properties": {
                  "component": { "enum": ["HoursCard", "BookingForm", "CateringQuoteForm"] }
                }
              }
            ]
          }
        }
      }
    },
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "topic"],
      "properties": {
        "kind": { "const": "gap" },
        "topic": { "type": "string", "maxLength": 60 }
      }
    },
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind"],
      "properties": { "kind": { "const": "off_topic" } }
    }
  ]
}
```

Schema-building rules:

- The enums are filled from this request's candidates. A field whose candidate list is empty
  gets `[null]` (diet, section) or is omitted with its variant (`Answer` with no FAQ retrieved,
  `AllergenNotice` with no Allergen retrieved). Never emit an empty `enum`.
- With zero candidates, only the `gap` and `off_topic` branches are offered.
- `MenuList.order` is `true` only when the visitor wants to order (pick up, take out, add).
  "Do you have vegetarian options?" is `false`: they want to know, not order.
- `MenuList` filters combine: diet and section narrow the list; `items` names specific dishes.
- `topic` is a short noun phrase for what could not be answered ("gluten-free pasta"). It is
  the only free text the model writes, and it goes only to the owner side.
- There is no allergen filter on `MenuList`. Allergen questions route to `AllergenNotice`.
- Request settings: temperature 0, `max_tokens` 96, thinking disabled per request with
  `chat_template_kwargs: {"enable_thinking": false}`, compact JSON (on vLLM set
  `disable_any_whitespace` in the structured-output config). Confirm in the first 30 minutes
  that the schema is still enforced with thinking off.
- The system prompt is stable (catalog `use_when` lines first, then candidates as
  `id | label | name | key facts`, then the visitor's text last) so prefix caching can hit.
  Candidate lines carry only `name`, typed fields, and a capped description, inside a
  delimited data block.

Examples:

| Visitor types | Selection |
|---|---|
| vegetarian options | `{"kind":"answer","views":[{"component":"MenuList","diet":"diet_vegetarian","section":null,"items":[],"order":false}]}` |
| I want to pick up something vegetarian | same with `"order":true` |
| are you open on the 4th of July? | `{"kind":"answer","views":[{"component":"HoursCard"}]}` |
| do you cater for 40? | `{"kind":"answer","views":[{"component":"CateringQuoteForm"}]}` |
| do you have gluten-free pasta? (nothing verified) | `{"kind":"gap","topic":"gluten-free pasta"}` |
| I'm allergic to peanuts | `{"kind":"answer","views":[{"component":"AllergenNotice","allergen":"alg_peanuts"}]}` |
| tell me a joke | `{"kind":"off_topic"}` |

### 8.2 Slots (code, before the model)

Slots are extracted by code and never by the model: `date` (YYYY-MM-DD), `time` (HH:MM),
`party_size`, `headcount`. A date with no year resolves to its next occurrence on or after
today in `CAC_TZ`; on 3 October 2026, "the 4th of July" is 2027-07-04. Normalizing a text
means lowercase, trim, collapse whitespace, strip punctuation.

### 8.3 Binder (code, after the model)

1. **Validate.** Reject a view whose component is not approved, whose ids were not candidates,
   or whose node labels do not match `binds`. De-duplicate ids; keep the first view per
   component. On failure retry the model once with the error; on a second failure, a timeout
   (6 s), or more than `MODEL_MAX_INFLIGHT` calls in flight, return the `menu` preset with a
   "we're busy" note and `meta.cache = "preset"`.
2. **Gap.** For `kind: gap`, return the fixed gap surface: "We haven't confirmed that yet.
   Please ask our staff." with the phone link from the Business node. Log `gap_topic`.
3. **Off topic.** Return the fixed surface "I can help with our menu, hours, bookings and
   catering." with default chips. Logged, never turned into a gap.
4. **MenuList.** Build the list in code: items in the chosen section, items with an approved
   `SUITABLE_FOR` edge to the chosen diet (owner-verified first), or the named items. Title
   comes from the Diet or Section node's name. Cap at 12 with a "Full menu" link to the
   `menu` preset. `order: true` adds the `add_to_cart` action.
5. **Diet and allergen facts.** A diet badge is shown only for an owner-verified edge; an
   unverified one renders "not verified, ask staff". An allergen never produces a list of safe
   dishes: `AllergenNotice` with an allergen shows the fixed text "We cannot guarantee any dish
   is free of {allergen}. Please tell your server about your allergy." and lists only dishes
   with an owner-verified `CONTAINS_ALLERGEN` edge under "Confirmed to contain {allergen}".
6. **Slots.** `HoursCard`, `BookingForm` and `CateringQuoteForm` take date, time, party size
   and headcount from the slots. `HoursCard` computes open or closed for the date from
   SpecialHours first, then HoursSpec.
7. **Inserted components.** Add `AllergenNotice` (notice only) to any surface with a
   `MenuList`. Add at most one `GoalCTA`, and only when no view on the surface already carries
   a `steer` weight; use the highest-`steer` component and its `cta_label`. A catering question
   therefore gets the catering form and no booking button; an hours question gets a booking
   button.
8. **Words.** `say` comes from the catalog entry's `say` template (for `HoursCard`, the
   computed sentence; for `Answer`, nothing, because the FAQ answer is the content). Chips come
   from the entry's fixed `chips`. Nothing shown to a visitor is model-written or copied from
   another visitor.
9. **Text for agents.** Fill `text` for every view from a per-component template so assistants
   read graph facts.
10. **Consistency.** Retrieval and binding run in one `REPEATABLE READ, READ ONLY` transaction
    that also reads `graph_version`. The Serve API never caches the graph version or catalog in
    process memory, so a publish takes effect on the next request with no restart.

### 8.4 Surface (Serve API response)

```json
{
  "surface_id": "s_01HZX",
  "kind": "answer",
  "title": "Vegetarian",
  "say": "Here is what matches.",
  "views": [
    {
      "id": "v1",
      "component": "MenuList",
      "data": {
        "title": "Vegetarian",
        "items": [
          { "id": "mi_mushroom_risotto", "name": "Mushroom risotto", "price": "$24.00",
            "description": "Arborio rice, wild mushrooms, parmesan",
            "badges": [{ "diet": "Vegetarian", "verified": true }] }
        ],
        "more": null
      },
      "actions": [],
      "text": "Vegetarian (confirmed by the restaurant): Mushroom risotto, $24.00."
    },
    { "id": "v2", "component": "AllergenNotice", "data": { "allergen": null, "contains": [] },
      "actions": [],
      "text": "Before placing your order, please inform your server if a person in your party has a food allergy." },
    { "id": "v3", "component": "GoalCTA", "data": { "label": "Book a table" },
      "actions": [{ "name": "open_view:booking", "handler": "client" }], "text": "" }
  ],
  "chips": ["What desserts do you have?", "Book a table"],
  "meta": { "cache": "miss", "latency_ms": 1840, "graph_version": 7, "model": "local" }
}
```

`title` is the history-rail label (at most 24 characters): the first view's title or the
catalog entry's `rail_label`.

Data shapes per component:

| Component | `data` |
|---|---|
| `Answer` | `{ question, answer, verified, verified_at }`; `answer` is the FAQ text verbatim |
| `MenuList` | `{ title, items: [{ id, name, price, description, badges: [{ diet, verified }] }], more }` |
| `HoursCard` | `{ date, status: "open" \| "closed" \| null, opens, closes, note, week: [{ days, opens, closes }] }` |
| `BookingForm` | `{ prefill: { date?, time?, party_size? }, booking_url? }` |
| `CateringQuoteForm` | `{ prefill: { headcount?, date? }, min_headcount }` |
| `AllergenNotice` | `{ allergen, contains: [{ id, name }] }` |
| `GoalCTA` | `{ label }` |

Form payloads (also the MCP tool inputs):

| Action | Payload |
|---|---|
| `submit_booking_request` | `{ date, time, party_size (1..20), name, contact, notes? }` |
| `submit_catering_quote` | `{ date, headcount, name, contact, notes? }` |

A failed submit returns HTTP 422 `{ "ok": false, "errors": [{ "field", "message" }] }`. A date
in the past is an error.

### 8.5 Serve API

| Method | Path | Body | Returns | Model call |
|---|---|---|---|---|
| GET | `/v1/bootstrap` | — | `{ business: { name, tagline }, theme, nav: [{ label, preset }], chips }` | never |
| POST | `/v1/intent` | `{ "text", "session_id", "context"? }` | Surface | once, only on a cache miss |
| GET | `/v1/view/{preset}` | — | Surface | never |
| POST | `/v1/action` | `{ "name", "payload", "session_id", "component" }` | `{ "ok", "surface"? }` | never |
| GET | `/v1/metrics` | — | see below | never |
| GET | `/healthz` | — | status of database, model, embedder | never |
| GET | `/embed.js`, `/widget/` | — | the embed script and the widget | never |

Intent pipeline:

1. Validate: `text` is 1 to 300 characters, else HTTP 422.
2. Normalize and extract slots.
3. Exact cache lookup on (`normalized_hash`, `slots_key`, `graph_version`). On a hit, re-bind
   the cached selection against the current graph.
4. On a miss: retrieve, build the schema, make one model call, validate, bind, store the
   selection.
5. Log every request, including cache hits, with `kind` and `gap_topic`.

Other rules:

- The server sets `channel` from the caller (the widget is `web`; the MCP server identifies
  itself with an internal header and is `mcp`). It is never taken from the request body.
- Action payloads are untrusted. Validate them and re-check every referenced id in
  `kg_public`. Lead submissions are limited to 3 per session per hour (10 per hour in total on
  the `mcp` channel).
- CORS allows only `CAC_ALLOWED_ORIGINS`.
- `/v1/metrics` returns latency percentiles, cache hit rate, in-flight model calls, graph
  version, leads captured, goal CTAs shown and clicked, and `model_host` (the resolved model
  endpoint). Counters are kept in process, because `cac_serve` cannot read the log.
- P1, refinement ("only desserts"): `context` carries the current `MenuList` filter; the model
  returns a new filter and the binder intersects the two. Requests with `context` bypass the
  cache.
- P1, slot masking: selections with no ids (`HoursCard`, `BookingForm`, `CateringQuoteForm`)
  are cached under a key with slot values masked, so "open on <any date>" costs one model call
  ever.

### 8.6 Owner tools API

REST on port 8081, `Authorization: Bearer $OWNER_TOOLS_TOKEN`, bound to the address the
sandbox can reach and to nothing public. The agent calls it through one OpenClaw skill. If
plain HTTP from the sandbox is blocked, the alternative is to expose the same endpoints as a
Streamable HTTP MCP server registered with NemoClaw; settle this in the first 30 minutes.

| Endpoint | Input | Effect | Agent may call |
|---|---|---|---|
| `GET /owner/gaps?state=open` | — | Folds new `ops.intent_log` rows with `kind = 'gap'` into KnowledgeGap nodes keyed on the lowercased topic (using the watermark in `ops.sync_state`), then returns `[{ gap_id, topic, count }]` for gaps seen in at least `GAP_ASK_MIN_SESSIONS` sessions. Never returns visitor text or session ids | yes |
| `POST /owner/gaps/{id}/asked` | — | Marks the gap `asked`. Only one gap may be `asked` at a time, so an owner reply maps to exactly one question | yes |
| `POST /owner/answers` | `{ gap_id, answer_text }` (at most 400 characters) | Accepted only for a gap in state `asked`. Creates an FAQ node (`question` = a templated question from the topic, `answer` = the owner's words verbatim) with `visibility = public`, `status = approved`, `source_type = owner`, `verified_by_owner = true`, `verified_at = now()`; builds `search_text`; embeds it; adds `ANSWERS` and `ABOUT` edges; marks the gap `answered` | yes |
| `POST /owner/special-hours` | `{ date, closed, opens?, closes?, note? }` | Creates an owner-verified SpecialHours node, so "we're closed on the 24th" becomes data that code answers from | yes |
| `POST /owner/publish` | — | Calls `kg.publish()`, then replays the top 20 intents and the demo intent list through `/v1/intent` with channel `prewarm`. Returns `{ graph_version }` | yes |
| `GET /owner/digest` | — | `{ questions_today, top_topics, open_gaps, new_leads: [{ kind, count }] }`: counts only, no customer details | yes |
| `GET /owner/inbox` | — | Read-only HTML page for the owner: new leads with details, open gaps with example questions. For a person, not the agent | no |

What the agent cannot do, by construction: read visitor text or lead details, create any node
other than an FAQ or SpecialHours, verify a diet or allergen edge, approve a draft, or change
visibility. The owner channel accepts messages only from `OWNER_CHANNEL_USER_ID`. The question
sent to the owner is a code template around the topic: "{count} visitors asked about {topic}.
I have nothing confirmed. What should I tell them?"

P1 endpoints: `POST /owner/drafts` (always private, draft, `source_type = agent`),
`POST /owner/proposals` (a `FormCard` entry for owner approval), batch verification of diet
tags, and owner-initiated facts. Before any of these publishes, the API echoes the final text
to the owner for a yes.

### 8.7 MCP server

Stateless Streamable HTTP at `POST /mcp`. It holds no database credentials: every tool is a
call to the Serve API on localhost. Only `/mcp` is routed through the tunnel.

Pins from Anthropic's quickstart: `@modelcontextprotocol/ext-apps@1.7.5` and
`@modelcontextprotocol/sdk@1.30.1`. Do not install ext-apps 2.x. Add the tunnel hostname to
`allowedHosts`, or requests fail with 403. On a Cloudflare Quick Tunnel set
`enableJsonResponse: true`; prefer a tunnel with a stable hostname, because the connector is
registered by URL.

| Tool | Input | Output | Notes |
|---|---|---|---|
| `get_business_profile` | — | Name, cuisine, address, hours summary, price range, services (from `/v1/bootstrap` and the `hours` preset) | |
| `ask_restaurant` | `{ "question" }` | `content`: the views' `text` joined; `structuredContent`: the Surface | Declared with `_meta: { ui: { resourceUri: "ui://cac/surface.html" } }` on the tool definition. Description: "Ask <restaurant name> (Cambridge, MA) about its menu, dietary options, hours, bookings or catering. Returns facts confirmed by the restaurant and an interactive card." |
| `get_view` | `{ "preset" }` | Surface | App-only; lets buttons in the component open presets |
| `request_booking` | booking payload (8.4) | Lead id and "request received; the restaurant will confirm" | |
| `request_catering_quote` | catering payload (8.4) | Lead id and next step | |

The `ui://cac/surface.html` resource (MIME `text/html;profile=mcp-app`) is the widget bundle
built as a single HTML file with no external origins. The widget takes a `transport` with
`intent(text)`, `view(preset)` and `action(name, payload)`: the web build implements it with
`fetch`; the MCP App build implements it with host tool calls (`ask_restaurant`, `get_view`,
`request_booking`, `request_catering_quote`).

### 8.8 A2A agent card (P2)

Serve a card at `/.well-known/agent-card.json` generated with the A2A SDK, advertising the
same skills. Do not hand-write the card and do not publish one that points at nothing.

## 9. Seed

One seed file describes the fictional demo restaurant and drives both the graph and the static
demo site, so they cannot drift. Loading it writes approved public nodes with
`source_type = seed`.

```yaml
business:
  id: biz_demo
  name: <restaurant name>
  timezone: America/New_York
  cuisine: [Italian]
  phone: "+1 617 555 0100"
sections:
  - id: sec_mains
    name: Mains
    items:
      - { id: mi_mushroom_risotto, name: Mushroom risotto, price_cents: 2400,
          description: "Arborio rice, wild mushrooms, parmesan" }
      - { id: mi_ribeye, name: Ribeye, price_cents: 4200, description: "12 oz, herb butter" }
hours:
  - { days: [tue, wed, thu, fri, sat, sun], opens: "11:00", closes: "22:00" }
special_hours:
  - { id: sh_2027_07_04, date: 2027-07-04, closed: true, note: Independence Day }
  - { id: sh_2026_11_26, date: 2026-11-26, closed: true, note: Thanksgiving }
services:
  - { id: svc_reservations, kind: reservations }
  - { id: svc_catering, kind: catering, min_headcount: 15 }
verified_diets:            # owner-verified SUITABLE_FOR edges for the demo restaurant
  diet_vegetarian: [mi_mushroom_risotto]
unverified_diets:          # approved but not verified: must render "not verified, ask staff"
  diet_vegetarian: [mi_caprese]
goals:
  - { id: goal_bookings, statement: Fill tables on weeknights, priority: 5,
      advanced_by: [BookingForm] }
  - { id: goal_catering, statement: Sign up catering clients, priority: 4,
      advanced_by: [CateringQuoteForm] }
private:
  customers:
    - { id: cust_canary, name: "Zephyrine Quillfeather", contact: "canary@example.invalid" }
```

The loader writes Goal nodes and `ADVANCES` edges as approved and owner-verified, and resolves
`advanced_by` names to `ui_<component>` ids. Goal text never leaves `kg`.

## 10. Fixtures and tests

| Fixture or test | Pass condition |
|---|---|
| 30 intents with their expected component and filter | 100% schema-valid; at least 27 of 30 correct components |
| One golden Surface JSON per component | Widget renders each; committed before the pipeline exists so both sides can build in parallel |
| Permission check, run as `cac_serve` | `SELECT` on `kg.node`, `ops.lead` and `ops.intent_log` each return "permission denied" |
| Canary script | Put the canary name in a Customer node, a lead payload, and an intent log row. Send the 30 intents plus 10 extraction prompts to `/v1/intent`, every preset, `/v1/metrics`, and each MCP tool. Fail if any response contains the canary |
| Unverified diet edge (`mi_caprese`) | Renders "not verified, ask staff", never a badge |
| "nut-free dishes", "I'm allergic to peanuts" | No `MenuList` of safe dishes; `AllergenNotice` only |
| Date resolver pinned to 2026-10-03 | "4th of July" → 2027-07-04 (closed); "Thanksgiving" → 2026-11-26 (closed) |
| Gap loop | An unknown question logs a gap; after `POST /owner/answers` and publish, the same question returns `Answer` with `verified: true`, with no restart |
| Goal steer | Hours question returns a booking CTA; catering question returns the catering form and no booking CTA |
| Private prop on a public node | A `supplier` prop on a MenuItem does not appear in `kg_public` |
| Two-friends question through MCP | At least one owner-verified vegetarian main, one meat main, and a booking CTA |
