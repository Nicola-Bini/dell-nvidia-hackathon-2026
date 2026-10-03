-- Full-text and trigram search over search_text: the retrieval fallback when no embedding
-- model is available (docs/SCHEMA.md section 6). Kept apart from schema.sql, which is the
-- section 4 DDL verbatim. Run once as the bootstrap superuser, after schema.sql:
--   psql -f search.sql
-- Safe to run again.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS public_node_search_tsv_idx
  ON kg_public.node USING gin (to_tsvector('english', search_text));
CREATE INDEX IF NOT EXISTS public_node_search_trgm_idx
  ON kg_public.node USING gin (search_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS node_search_tsv_idx
  ON kg.node USING gin (to_tsvector('english', search_text));
CREATE INDEX IF NOT EXISTS node_search_trgm_idx
  ON kg.node USING gin (search_text gin_trgm_ops);
