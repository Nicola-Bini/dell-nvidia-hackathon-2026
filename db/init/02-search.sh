#!/bin/sh
# Runs once, on first container start, as the bootstrap superuser, after 01-schema.sh.
# db/search.sql adds pg_trgm and the search_text indexes for the full-text fallback.
set -eu
psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -f /schema/search.sql
