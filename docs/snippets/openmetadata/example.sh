#!/usr/bin/env bash
# Starts metadata, registers PostgreSQL as a database service, runs a metadata
# ingestion of the omt database, counts the searchable tables and removes the
# service again.
set -euo pipefail

odctl up metadata
om=http://127.0.0.1:8585/api/v1
json() { python3 -c "import json, sys; print($1)"; }

TOKEN=$(curl -s -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin@open-data.local\",\"password\":\"$(printf admin | base64)\"}" \
  "$om/users/login" | json 'json.load(sys.stdin)["accessToken"]')
AUTH="Authorization: Bearer $TOKEN"

SVC=$(curl -s -X PUT -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"demo_pg","serviceType":"Postgres","connection":{"config":{"type":"Postgres","scheme":"postgresql+psycopg2","username":"user","authType":{"password":"password"},"hostPort":"postgres:5432","database":"omt"}}}' \
  "$om/services/databaseServices" | json 'json.load(sys.stdin)["id"]')

PIPE=$(curl -s -X POST -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"demo_pg_metadata\",\"pipelineType\":\"metadata\",\"service\":{\"id\":\"$SVC\",\"type\":\"databaseService\"},\"sourceConfig\":{\"config\":{\"type\":\"DatabaseMetadata\"}},\"airflowConfig\":{\"startDate\":\"2026-01-01T00:00:00.000Z\"}}" \
  "$om/services/ingestionPipelines" | json 'json.load(sys.stdin)["id"]')
# The server deploys the pipeline into the ingestion Airflow, which answers a
# little after the server.
until curl -fs http://127.0.0.1:8087/api/v2/monitor/health >/dev/null; do sleep 5; done
until curl -s -X POST -H "$AUTH" "$om/services/ingestionPipelines/deploy/$PIPE" \
  | grep 'has been created' >/dev/null; do sleep 5; done

# Airflow parses the new DAG file before the trigger works.
until curl -s -X POST -H "$AUTH" "$om/services/ingestionPipelines/trigger/$PIPE" \
  | grep 'has been triggered' >/dev/null; do sleep 5; done

state=""
until [ "$state" = success ] || [ "$state" = failed ]; do
  sleep 10
  state=$(curl -s -H "$AUTH" \
    "$om/services/ingestionPipelines/name/demo_pg.demo_pg_metadata?fields=pipelineStatuses" \
    | json '(json.load(sys.stdin).get("pipelineStatuses") or [{}])[0].get("pipelineState", "")')
done
echo "ingestion: $state"

# The search index fills over a few minutes after it is rebuilt.
curl -s -X POST -H "$AUTH" "$om/apps/trigger/SearchIndexingApplication" >/dev/null
hits=0
until [ "$hits" -gt 100 ]; do
  sleep 5
  hits=$(curl -s -H "$AUTH" "$om/search/query?q=*&index=table_search_index&size=1" \
    | json 'json.load(sys.stdin)["hits"]["total"]["value"]')
done
echo "searchable tables: $hits"

curl -s -X DELETE -H "$AUTH" \
  "$om/services/databaseServices/name/demo_pg?hardDelete=true&recursive=true" >/dev/null
echo "removed demo_pg"
