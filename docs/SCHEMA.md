# CAC — Schema and Contracts

Companion to [PRD.md](PRD.md). This file is the source of truth for scaffolding: the graph
store, the label and edge registries, the UI component catalog, and the wire contracts between
the model, the Serve API, the widget, and external agents.

## 1. Design rules

1. **Default private.** A node is private and draft until someone labels it public and the owner
   approves it. Nothing reaches a visitor or an external agent before `kg.publish()` copies it.
2. **The partition is enforced by the database, not the prompt.** Serving processes connect as
   `cac_serve`, which has no grant on the `kg` schema. They can only read `kg_public`.
3. **No mixed nodes.** A public node carries only public props. A private fact about a public
   thing (item margin, supplier) lives in a separate private node linked by an edge.
4. **The model picks, code fills.** The model returns a component name and node ids. Names,
   prices, hours, and diet badges are read from the graph by the binder. The model never writes
   an allergen or diet claim.
5. **No model-written queries.** Retrieval is vector entry plus fixed expansion templates.
6. **Provenance on everything.** Every node and edge records where it came from and whether the
   owner verified it.

## 2. Storage layout

One Postgres container with pgvector (`pgvector/pgvector:pg18-trixie`, arm64 image exists).

| Schema | Contents | `cac_owner` | `cac_serve` |
|---|---|---|---|
| `kg` | Full graph: public, private, drafts, goals, gaps | read/write | no access |
| `kg_public` | Published projection: approved public nodes and edges | write via `publish()` | read only |
| `ops` | Intent log, cache, leads | read/write | insert log and leads, read/write cache |

Who connects as what:

- `cac_serve`: Serve API and MCP server (everything a visitor or external agent can reach).
- `cac_owner`: ingestion, owner tools API, and through it the NemoClaw agents.
- The image's default `postgres` user is a superuser and bypasses row security. Use it once for
  bootstrap and never from an application.

## 3. DDL

Set the vector dimension to match the embedding model before creating tables (1024 fits
`bge-m3` and `qwen3-embedding:0.6b`; `nomic-embed-text` is 768).

```sql
-- Run once as the bootstrap superuser. Passwords come from the environment, not this file.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE cac_owner LOGIN;
CREATE ROLE cac_serve LOGIN;

CREATE SCHEMA kg AUTHORIZATION cac_owner;
CREATE SCHEMA kg_public AUTHORIZATION cac_owner;
CREATE SCHEMA ops AUTHORIZATION cac_owner;

SET ROLE cac_owner;

-- 3.1 Label registry: which labels may ever be published
CREATE TABLE kg.label (
  label          text PRIMARY KEY,
  may_be_public  boolean NOT NULL,
  description    text NOT NULL
);

-- 3.2 Full graph
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
  valid_from         timestamptz,
  valid_to           timestamptz,
  search_text        text NOT NULL DEFAULT '',    -- the text that gets embedded
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

-- 3.3 Published projection: the only graph the serving role can read
CREATE TABLE kg_public.node (
  id                 text PRIMARY KEY,
  business_id        text NOT NULL,
  label              text NOT NULL,
  name               text NOT NULL,
  props              jsonb NOT NULL,
  verified_by_owner  boolean NOT NULL,
  valid_from         timestamptz,
  valid_to           timestamptz,
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

-- 3.4 Publish: the owner-approved step that moves data across the boundary
CREATE FUNCTION kg.publish(p_business text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
  v_version integer;
BEGIN
  DELETE FROM kg_public.node WHERE business_id = p_business;  -- edges cascade

  INSERT INTO kg_public.node
    (id, business_id, label, name, props, verified_by_owner,
     valid_from, valid_to, search_text, embedding)
  SELECT n.id, n.business_id, n.label, n.name, n.props, n.verified_by_owner,
         n.valid_from, n.valid_to, n.search_text, n.embedding
  FROM kg.node n
  JOIN kg.label l ON l.label = n.label
  WHERE n.business_id = p_business
    AND n.visibility = 'public'
    AND n.status = 'approved'
    AND l.may_be_public;

  INSERT INTO kg_public.edge (src, dst, type, props, verified_by_owner)
  SELECT e.src, e.dst, e.type, e.props, e.verified_by_owner
  FROM kg.edge e
  WHERE e.business_id = p_business
    AND e.status = 'approved'
    AND EXISTS (SELECT 1 FROM kg_public.node s WHERE s.id = e.src)
    AND EXISTS (SELECT 1 FROM kg_public.node d WHERE d.id = e.dst);

  -- Goals stay private; components only receive a numeric steering weight.
  UPDATE kg_public.node c
  SET props = c.props || jsonb_build_object('steer', s.weight)
  FROM (
    SELECT e.src AS component_id, max((g.props ->> 'priority')::integer) AS weight
    FROM kg.edge e
    JOIN kg.node g ON g.id = e.dst
    WHERE e.business_id = p_business
      AND e.type = 'ADVANCES' AND e.status = 'approved'
      AND g.label = 'Goal' AND g.status = 'approved'
    GROUP BY e.src
  ) s
  WHERE c.id = s.component_id;

  INSERT INTO kg_public.meta (business_id, graph_version, published_at)
  VALUES (p_business, 1, now())
  ON CONFLICT (business_id) DO UPDATE
    SET graph_version = kg_public.meta.graph_version + 1, published_at = now()
  RETURNING graph_version INTO v_version;

  RETURN v_version;
END $$;

-- 3.5 Runtime tables
CREATE TABLE ops.intent_log (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ts             timestamptz NOT NULL DEFAULT now(),
  business_id    text NOT NULL,
  channel        text NOT NULL CHECK (channel IN ('web', 'nav', 'mcp', 'a2a')),
  session_id     text,
  text           text NOT NULL,                  -- raw visitor text: treat as private
  normalized     text NOT NULL,
  slots          jsonb NOT NULL DEFAULT '{}'::jsonb,
  cache          text NOT NULL CHECK (cache IN ('exact', 'semantic', 'miss', 'preset')),
  selection      jsonb,
  gap            text,                           -- what the graph could not answer, if anything
  latency_ms     integer NOT NULL,
  model          text,
  graph_version  integer NOT NULL
);

CREATE TABLE ops.intent_cache (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  business_id    text NOT NULL,
  graph_version  integer NOT NULL,
  normalized     text NOT NULL,
  slots_key      text NOT NULL,                  -- canonical string of extracted slots
  embedding      vector(1024),
  selection      jsonb NOT NULL,                 -- the model's choice, never hydrated data
  hits           integer NOT NULL DEFAULT 0,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (business_id, graph_version, normalized, slots_key)
);

CREATE TABLE ops.lead (
  id           uuid PRIMARY KEY,                 -- generated by the caller, so no RETURNING needed
  ts           timestamptz NOT NULL DEFAULT now(),
  business_id  text NOT NULL,
  kind         text NOT NULL
               CHECK (kind IN ('booking_request', 'catering_quote', 'pickup_order', 'contact')),
  payload      jsonb NOT NULL,                   -- contains customer PII: private, on the box only
  channel      text NOT NULL,
  session_id   text,
  status       text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'confirmed', 'declined'))
);

-- 3.6 Grants: cac_serve never receives anything on schema kg
GRANT USAGE ON SCHEMA kg_public TO cac_serve;
GRANT SELECT ON ALL TABLES IN SCHEMA kg_public TO cac_serve;
GRANT USAGE ON SCHEMA ops TO cac_serve;
GRANT INSERT ON ops.intent_log, ops.lead TO cac_serve;
GRANT SELECT, INSERT, UPDATE ON ops.intent_cache TO cac_serve;

RESET ROLE;
```

## 4. Label registry

Seed `kg.label` with these rows. Id prefixes keep ids readable in logs and prompts.

| Label | Prefix | May be public | Key props | schema.org source |
|---|---|---|---|---|
| Business | `biz_` | yes | `cuisine[]`, `price_range`, `phone`, `url`, `tagline` | `Restaurant` |
| Location | `loc_` | yes | `street`, `city`, `region`, `postal`, `lat`, `lng`, `parking`, `transit` | `PostalAddress`, `GeoCoordinates` |
| HoursSpec | `hrs_` | yes | `days[]` (mon..sun), `opens`, `closes`, `service` (dine_in, kitchen, bar) | `OpeningHoursSpecification` |
| SpecialHours | `sh_` | yes | `date`, `closed`, `opens`, `closes`, `note` | `specialOpeningHoursSpecification` |
| Menu | `menu_` | yes | `kind` (dinner, lunch, drinks, catering) | `Menu` |
| MenuSection | `sec_` | yes | `position` | `MenuSection` |
| MenuItem | `mi_` | yes | `description`, `price_cents`, `currency`, `course`, `image_id`, `available` | `MenuItem`, `Offer` |
| Ingredient | `ing_` | yes | — | — |
| Allergen | `alg_` | yes | `fda_major` (bool) | none (custom) |
| Diet | `diet_` | yes | `schema_org` (e.g. `VegetarianDiet`) | `RestrictedDiet` |
| Service | `svc_` | yes | `kind` (dine_in, takeout, catering, private_events, reservations), `details`, `min_headcount` | `acceptsReservations` etc. |
| FAQ | `faq_` | yes | `question`, `answer` | `FAQPage` |
| ReviewSummary | `rev_` | yes | `rating`, `count`, `source`, `highlights[]` | `AggregateRating` |
| BrandTrait | `trait_` | yes | `kind` (vibe, tone, color, font), `value` | — |
| MediaAsset | `img_` | yes | `url`, `alt` | `ImageObject` |
| Promotion | `promo_` | yes | `details`, `days[]` | `Offer` |
| UIComponent | `ui_` | yes | catalog entry (section 6) | — |
| Intent | `int_` | yes | `examples[]`, `kind` (know, order, book, contact) | — |
| Action | `act_` | yes | `handler` (client, server), `payload_schema` | — |
| Goal | `goal_` | **no** | `statement`, `priority` (1..5), `metric` | — |
| KnowledgeGap | `gap_` | **no** | `question`, `count`, `examples[]`, `state` (open, asked, answered) | — |
| Proposal | `prop_` | **no** | `kind` (node, edge, component, intent), `draft`, `reason` | — |
| Customer | `cust_` | **no** | `name`, `contact`, `notes` | — |
| OwnerNote | `note_` | **no** | `text` | — |

`search_text` per label is a short generated sentence, for example for a MenuItem:
`"Mushroom risotto. Main course. Arborio rice, wild mushrooms, parmesan. $24."`

## 5. Edge registry

| Type | From → To | Props | Notes |
|---|---|---|---|
| `HAS_LOCATION` | Business → Location | — | |
| `HAS_HOURS` | Business → HoursSpec, SpecialHours | — | Open/closed is computed in code |
| `HAS_MENU` | Business → Menu | — | |
| `HAS_SECTION` | Menu → MenuSection | — | |
| `HAS_ITEM` | MenuSection → MenuItem | `position` | |
| `CONTAINS` | MenuItem → Ingredient | — | |
| `CONTAINS_ALLERGEN` | MenuItem → Allergen | — | Rendered as fact only if `verified_by_owner` |
| `SUITABLE_FOR` | MenuItem → Diet | — | Badge shown only if `verified_by_owner` |
| `PAIRS_WITH` | MenuItem → MenuItem | `reason` | Upsell suggestions |
| `OFFERS` | Business → Service, Promotion | — | |
| `HAS_TRAIT` | Business → BrandTrait | — | Drives widget theme and tone |
| `HAS_REVIEWS` | Business → ReviewSummary | — | |
| `DEPICTS` | MediaAsset → any public node | — | |
| `ANSWERS` | FAQ → Service, MenuItem, Business | — | |
| `RENDERS_WITH` | Intent → UIComponent | `weight` | Retrieval returns the component with the data |
| `TRIGGERS` | UIComponent → Action | — | Deterministic path, no model call |
| `ADVANCES` | UIComponent → Goal | — | Never published; becomes `steer` weight |
| `ABOUT` | KnowledgeGap, Proposal → any node | — | Private |

Fixed expansion templates (run after vector entry, written by us, never by the model):

| Entry label | Expansion |
|---|---|
| Diet | items with `SUITABLE_FOR` to it (verified first), their sections |
| Allergen | items with `CONTAINS_ALLERGEN` to it, and all items lacking a verified edge |
| MenuItem | its section, ingredients, diets, allergens, `PAIRS_WITH` items |
| MenuSection, Menu | child items |
| Service | linked FAQ, Promotion |
| HoursSpec, SpecialHours | all hours nodes for the business |
| Intent | components via `RENDERS_WITH` |

## 6. UI component catalog

The catalog is the set of owner-approved `UIComponent` nodes. Each maps to one prebuilt React
component. The vocabulary (catalog, surface, action) follows Google's A2UI so the format can be
mapped to an A2UI catalog later; v0 does not ship an A2UI renderer.

Catalog entry (stored in `UIComponent.props`):

```json
{
  "component": "MenuList",
  "version": 1,
  "use_when": "Visitor asks what dishes exist, or filters by diet, ingredient, course or price.",
  "binds": { "label": "MenuItem", "min": 1, "max": 12 },
  "params": {},
  "optional_actions": ["add_to_cart"],
  "action_rule": "Include add_to_cart only when the visitor wants to order, not when they only want to know.",
  "channels": ["web", "mcp"],
  "selectable": true
}
```

Catalog for the hackathon build:

| Component | Use when | Binds | Params | Actions | Priority |
|---|---|---|---|---|---|
| `Answer` | A short factual reply is enough, or nothing else fits | none | — | — | P0 |
| `MenuList` | Dishes, diets, courses, prices | MenuItem[1..12] | — | `add_to_cart` (optional) | P0 |
| `ItemCard` | One specific dish | MenuItem[1] | — | `add_to_cart` (optional) | P0 |
| `HoursCard` | Opening hours, "are you open on…" | HoursSpec, SpecialHours | `date?` | `open_view:BookingForm` | P0 |
| `BookingForm` | Wants a table | Service[reservations] | `date?`, `time?`, `party_size?` | `submit_booking_request` | P0 |
| `CateringQuoteForm` | Catering, large groups, events | Service[catering] | `headcount?`, `date?` | `submit_catering_quote` | P0 |
| `LocationCard` | Address, directions, parking, contact | Location | — | `directions`, `call` | P0 |
| `ReviewHighlights` | Reputation, "is it good" | ReviewSummary | — | — | P1 |
| `Cart` | Visitor has added items | client state | — | `submit_pickup_order` | P1 |
| `AllergenNotice` | Inserted by the binder, never chosen by the model | Allergen, Diet edges | — | — | P0 |
| `GoalCTA` | Inserted by the binder from `steer` weights | UIComponent | — | `open_view:<component>` | P0 |

Actions:

| Action | Handler | Effect |
|---|---|---|
| `add_to_cart`, `remove_from_cart` | client | Updates widget cart state |
| `open_view:<component>` | client → `GET /v1/view/{preset}` | Shows a preset surface, no model call |
| `submit_booking_request` | server | Inserts `ops.lead` (`booking_request`); a request, not a confirmed reservation |
| `submit_catering_quote` | server | Inserts `ops.lead` (`catering_quote`) |
| `submit_pickup_order` | server | Inserts `ops.lead` (`pickup_order`); no payment |
| `directions`, `call` | client | Opens map or dialer link |

Navigation presets (the existing nav bar uses the same system with zero model calls):

| Nav | Preset surface |
|---|---|
| Menu | `MenuList` per section |
| Booking | `BookingForm` |
| Reviews | `ReviewHighlights` |
| Contact | `LocationCard` + `HoursCard` |

## 7. Wire contracts

### 7.1 Selection (model output)

The Serve API builds this JSON Schema per request and passes it to the local model as a
structured-output constraint. `component` is limited to approved catalog entries and `node_ids`
to the ids retrieved for this request, so the model cannot name anything else.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["say", "views", "followups", "gap"],
  "properties": {
    "say": { "type": "string", "maxLength": 160 },
    "views": {
      "type": "array",
      "maxItems": 3,
      "items": {
        "anyOf": [
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["component", "title", "node_ids", "actions"],
            "properties": {
              "component": { "const": "MenuList" },
              "title": { "type": "string", "maxLength": 60 },
              "node_ids": {
                "type": "array", "minItems": 1, "maxItems": 12,
                "items": { "enum": ["mi_mushroom_risotto", "mi_caprese", "mi_ribeye"] }
              },
              "actions": { "type": "array", "items": { "enum": ["add_to_cart"] } }
            }
          },
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["component", "params"],
            "properties": {
              "component": { "const": "HoursCard" },
              "params": {
                "type": "object",
                "additionalProperties": false,
                "properties": { "date": { "type": "string" } }
              }
            }
          }
        ]
      }
    },
    "followups": { "type": "array", "maxItems": 3, "items": { "type": "string", "maxLength": 40 } },
    "gap": { "anyOf": [{ "type": "null" }, { "type": "string", "maxLength": 120 }] }
  }
}
```

Rules:

- `say` is one friendly sentence. It must not contain prices, hours, or allergen statements;
  those come from components. Agent channels do not use `say` for facts (see 7.2 `text`).
- `gap` is set when the retrieved nodes cannot answer the question. The request is logged and
  becomes a `KnowledgeGap`.
- Length limits are re-checked by the validator, since not every decoding backend enforces them.
- Target under 60 output tokens. Temperature 0. Thinking disabled.

Example for "vegetarian options":

```json
{
  "say": "Here are our vegetarian dishes.",
  "views": [
    { "component": "MenuList", "title": "Vegetarian",
      "node_ids": ["mi_mushroom_risotto", "mi_caprese"], "actions": [] }
  ],
  "followups": ["Show only desserts", "Book a table"],
  "gap": null
}
```

### 7.2 Surface (Serve API response)

The binder validates the selection, loads nodes from `kg_public`, computes derived values, adds
system components, and returns a surface.

```json
{
  "surface_id": "s_01HZX",
  "say": "Here are our vegetarian dishes.",
  "views": [
    {
      "id": "v1",
      "component": "MenuList",
      "props": { "title": "Vegetarian" },
      "data": {
        "items": [
          { "id": "mi_mushroom_risotto", "name": "Mushroom risotto", "price": "$24.00",
            "description": "Arborio rice, wild mushrooms, parmesan",
            "badges": [{ "diet": "Vegetarian", "verified": true }] }
        ]
      },
      "actions": [],
      "text": "Vegetarian dishes: Mushroom risotto ($24.00)."
    },
    { "id": "v2", "component": "AllergenNotice", "props": {}, "data": { "unverified": [] },
      "actions": [], "text": "Before ordering, tell your server about any food allergy." },
    { "id": "v3", "component": "GoalCTA", "props": { "label": "Book a table" }, "data": {},
      "actions": [{ "name": "open_view:BookingForm", "handler": "client" }], "text": "" }
  ],
  "followups": ["Show only desserts", "Book a table"],
  "meta": { "cache": "miss", "latency_ms": 1840, "graph_version": 7, "model": "local" }
}
```

Binder rules:

1. Reject a view whose component is not approved, whose node ids were not in the candidate set,
   or whose node labels do not match the component's `binds`. One retry with the error, then
   fall back to `Answer`.
2. Read data only through the `cac_serve` connection.
3. Compute in code: open or closed for a date, price formatting, diet and allergen badges (only
   from verified edges; otherwise "not verified, ask staff").
4. Insert `AllergenNotice` whenever a view involves a Diet or Allergen. Insert at most one
   `GoalCTA`, for the highest `steer` component not already shown.
5. Fill `text` for every view from a per-component template. External agents receive this text,
   so facts they read are graph facts, not model prose.

### 7.3 Serve API

| Method | Path | Body | Returns | Model call |
|---|---|---|---|---|
| POST | `/v1/intent` | `{ "text", "session_id", "channel", "context": { "surface_id"? } }` | Surface | only on cache miss |
| GET | `/v1/view/{preset}` | — | Surface | never |
| POST | `/v1/action` | `{ "name", "payload", "session_id" }` | `{ "ok", "surface"? }` | never |
| GET | `/v1/metrics` | — | latency percentiles, cache hit rate, in-flight, graph version | never |
| GET | `/healthz` | — | status of DB, model, embedder | never |

Intent pipeline: normalize → extract slots (date, time, party size, diet keywords) → exact cache
→ semantic cache (same `slots_key` required) → embed → top-k over `kg_public.node` → fixed
expansion → build schema → one constrained model call → validate → bind → cache selection → log.

Action payloads are untrusted input. Validate against the action's `payload_schema` and re-check
that every referenced node id exists in `kg_public`.

### 7.4 Owner tools API (localhost only, `cac_owner`)

Used by the NemoClaw agents and the ingestion job. Never exposed through the tunnel.

| Tool | Purpose |
|---|---|
| `list_gaps` | Open knowledge gaps, grouped, with counts and example questions |
| `upsert_draft` | Create or update a draft node or edge (agent proposals) |
| `record_owner_answer` | Write an owner-verified node or edge from an owner reply |
| `approve` / `reject` | Change status of a draft or proposal |
| `publish` | Call `kg.publish()` and return the new graph version |
| `top_intents` | Aggregated intent counts for the digest and cache pre-warming |

### 7.5 MCP server (external assistants)

Stateless Streamable HTTP at `POST /mcp`, connecting as `cac_serve` through the Serve API.

| Tool | Input | Output |
|---|---|---|
| `get_business_profile` | — | Name, cuisine, address, hours summary, price range, services |
| `ask_restaurant` | `{ "question": string }` | `content`: joined view `text`; `structuredContent`: Surface; `_meta.ui.resourceUri`: `ui://cac/surface.html` |
| `request_booking` | `{ "date", "time", "party_size", "name", "contact", "notes"? }` | Lead id and "request received, the restaurant will confirm" |
| `request_catering_quote` | `{ "date", "headcount", "name", "contact", "notes"? }` | Lead id and next step |

The `ui://cac/surface.html` resource is the same React component bundle as the website widget,
built as a single HTML file with no external origins.

### 7.6 A2A agent card (secondary)

Serve a card at `/.well-known/agent-card.json` generated with the A2A SDK, advertising the same
four skills. Do not hand-write the card and do not publish one that points at nothing.

## 8. Owner goals (seed format)

```yaml
business_id: biz_demo
goals:
  - id: goal_bookings
    statement: Fill tables on weeknights
    priority: 3
    advanced_by: [BookingForm]
  - id: goal_catering
    statement: Sign up catering clients
    priority: 2
    advanced_by: [CateringQuoteForm]
```

Loading this file creates private `Goal` nodes and `ADVANCES` edges. Publishing turns them into
`steer` weights on the components; the goal text itself never leaves `kg`.

## 9. Test fixtures the build must include

| Fixture | Purpose |
|---|---|
| A private `Customer` node with a unique canary name | Leak test: no endpoint may ever return the canary string |
| A MenuItem with an unverified `SUITABLE_FOR` edge | Must render "not verified, ask staff", never a badge |
| A `SpecialHours` node for a holiday | "Are you open on July 4th?" is answered by code |
| An intent with no supporting nodes (for example gluten-free pasta) | Must produce a `gap`, then a `KnowledgeGap` |
| A `Goal` with priority 3 on `BookingForm` | Hours question must come back with a booking CTA |
