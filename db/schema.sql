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
  description    text NOT NULL,
  locked         boolean NOT NULL DEFAULT false,  -- agent can never read or write these
  status         text NOT NULL DEFAULT 'approved' CHECK (status IN ('draft', 'approved', 'retired')),
  created_by     text NOT NULL DEFAULT 'seed' CHECK (created_by IN ('seed', 'agent', 'owner'))
);

-- Edge type registry: the agent can propose new relationship types
CREATE TABLE kg.edge_type (
  type           text PRIMARY KEY,
  public_props   text[] NOT NULL DEFAULT '{}',
  description    text NOT NULL,
  status         text NOT NULL DEFAULT 'approved' CHECK (status IN ('draft', 'approved', 'retired')),
  created_by     text NOT NULL DEFAULT 'seed' CHECK (created_by IN ('seed', 'agent', 'owner'))
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
  type               text NOT NULL REFERENCES kg.edge_type(type),
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

-- Every write by the agent (and by the owner through the inbox) is a change record.
CREATE TABLE kg.change (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ts           timestamptz NOT NULL DEFAULT now(),
  business_id  text NOT NULL,
  actor        text NOT NULL CHECK (actor IN ('agent', 'owner', 'ingest')),
  action       text NOT NULL CHECK (action IN (
                 'create_label', 'add_prop', 'create_edge_type',
                 'create_node', 'update_node', 'retire_node',
                 'create_edge', 'retire_edge',
                 'create_component', 'update_component')),
  target       text NOT NULL,                    -- label, edge type, node id or edge key
  before       jsonb,                            -- prior state, for revert
  after        jsonb NOT NULL,                   -- requested state
  reason       text NOT NULL,                    -- why, in the agent's words (shown to the owner)
  evidence     jsonb NOT NULL DEFAULT '{}'::jsonb, -- e.g. {"topic": "gift cards", "count": 12}
  tier         text NOT NULL CHECK (tier IN ('auto', 'one_tap', 'locked')),
  state        text NOT NULL CHECK (state IN ('pending', 'applied', 'rejected', 'reverted')),
  decided_by   text,
  decided_at   timestamptz
);
CREATE INDEX change_state_idx ON kg.change (business_id, state);

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
    AND l.may_be_public
    AND l.status = 'approved';

  INSERT INTO kg_public.edge (src, dst, type, props, verified_by_owner)
  SELECT e.src, e.dst, e.type,
         COALESCE((SELECT jsonb_object_agg(p.key, p.value)
                   FROM jsonb_each(e.props) AS p
                   WHERE p.key = ANY (t.public_props)), '{}'::jsonb),
         e.verified_by_owner
  FROM kg.edge e
  JOIN kg.edge_type t ON t.type = e.type
  WHERE e.business_id = p_business
    AND e.status = 'approved'
    AND t.status = 'approved'
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
