#!/usr/bin/env bash
# Starts trino and metabase, waits until every Trino catalog has loaded and
# Metabase answers, then lists the catalogs and runs a query.
set -euo pipefail

odctl up trino metabase

# Catalogs finish loading after Trino's health endpoint answers.
until docker exec trino trino --execute "SHOW CATALOGS" 2>/dev/null | grep '"valkey"' >/dev/null; do sleep 5; done
docker exec trino trino --execute "SHOW CATALOGS"
docker exec trino trino --execute "SELECT 1"

until curl -fs http://127.0.0.1:3000/api/health; do sleep 5; done
echo
