#!/usr/bin/env bash
# Wipes this box's database back to the demo starting point: the seed plus je's demo traffic
# (gift cards x12, parking x5). Run before a rehearsal, and after a load test (load-test
# traffic is logged and would show up as topics).
set -eu
. "$(dirname "$0")/lib.sh"
make -s db-reset seed | tail -1
(cd services/owner && uv run --no-dev python -m app.demo.seed_traffic | tail -1)
