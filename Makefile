# Shared targets only. Each lane keeps its own commands inside its own directory
# (see the lane file in docs/team/lanes/), so nobody but Blake needs to edit this file.
.PHONY: hooks env db-up db-reset db-check lane-check fixtures-check

hooks:            ## enable the pre-push lane guard
	git config core.hooksPath .githooks

env:              ## create .env from the example if it is missing
	@test -f .env || cp .env.example .env

db-up: env        ## start Postgres + pgvector and wait until healthy
	docker compose up -d --wait db

db-reset: env     ## drop the volume and re-run db/schema.sql
	docker compose down -v
	docker compose up -d --wait db

db-check:         ## privacy invariant: the serving role cannot read kg, leads or the log
	@for t in kg.node ops.lead ops.intent_log; do \
	  docker compose exec -T -e PGPASSWORD=$${CAC_SERVE_PASSWORD:-cac_serve_dev} db \
	    psql -h 127.0.0.1 -U cac_serve -d cac -c "select * from $$t limit 1" 2>&1 \
	    | grep -q "permission denied" \
	    && echo "ok: cac_serve denied on $$t" \
	    || { echo "FAIL: cac_serve can read $$t"; exit 1; }; \
	done

lane-check:       ## this branch only touches its own lane
	tools/lane-check

fixtures-check:   ## seed and golden fixtures are consistent
	uv run --with pyyaml python fixtures/validate.py
