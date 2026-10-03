# Shared targets only. Each lane keeps its own commands inside its own directory
# (see the lane file in docs/team/lanes/), so nobody but Blake needs to edit this file.
.PHONY: hooks env db-up db-reset db-check seed serve fake-llm lane-check fixtures-check

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

seed: env         ## load demo/kenmore into the graph and publish (safe to re-run)
	uv run --project tests python scripts/seed.py

serve: env        ## run the Serve API on SERVE_PORT (default 8080; the box uses 8082)
	cd services/serve && PYTHONPATH=src:../../packages/cac_common \
	  uv run uvicorn cac_serve.main:app --host $${SERVE_HOST:-127.0.0.1} \
	  --port $${SERVE_PORT:-$$(sed -n 's/^SERVE_PORT=//p' ../../.env | tail -1 | grep . || echo 8080)}

fake-llm:         ## laptop stand-in for the model on 127.0.0.1:8000
	uv run tools/fake_llm/server.py --port 8000

lane-check:       ## this branch only touches its own lane
	tools/lane-check

fixtures-check:   ## seed and golden fixtures are consistent
	uv run --with pyyaml python fixtures/validate.py
