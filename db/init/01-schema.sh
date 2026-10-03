#!/bin/sh
# Runs once, on first container start, as the bootstrap superuser.
# db/schema.sql is the DDL from docs/SCHEMA.md section 4, verbatim.
set -eu
psql -v ON_ERROR_STOP=1 \
  -v owner_pw="$CAC_OWNER_PASSWORD" \
  -v serve_pw="$CAC_SERVE_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -f /schema/schema.sql
