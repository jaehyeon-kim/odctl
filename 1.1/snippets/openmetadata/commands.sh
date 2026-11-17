# Commands from docs/guides/openmetadata.md. Each step uses the variables the
# steps before it set, so .github/scripts/smoke.sh runs a section with those
# variables set.

# --8<-- [start:login]
TOKEN=$(curl -s -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin@open-data.local\",\"password\":\"$(printf admin | base64)\"}" \
  http://127.0.0.1:8585/api/v1/users/login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["accessToken"])')
AUTH="Authorization: Bearer $TOKEN"
# --8<-- [end:login]

# --8<-- [start:service]
SVC=$(curl -s -X PUT -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"demo_pg","serviceType":"Postgres","connection":{"config":{"type":"Postgres","scheme":"postgresql+psycopg2","username":"user","authType":{"password":"password"},"hostPort":"postgres:5432","database":"omt"}}}' \
  http://127.0.0.1:8585/api/v1/services/databaseServices \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
# --8<-- [end:service]

# --8<-- [start:pipeline]
PIPE=$(curl -s -X POST -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"demo_pg_metadata\",\"pipelineType\":\"metadata\",\"service\":{\"id\":\"$SVC\",\"type\":\"databaseService\"},\"sourceConfig\":{\"config\":{\"type\":\"DatabaseMetadata\"}},\"airflowConfig\":{\"startDate\":\"2026-01-01T00:00:00.000Z\"}}" \
  http://127.0.0.1:8585/api/v1/services/ingestionPipelines \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/services/ingestionPipelines/deploy/$PIPE
curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/services/ingestionPipelines/trigger/$PIPE
# --8<-- [end:pipeline]

# --8<-- [start:status]
curl -s -H "$AUTH" \
  "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/name/demo_pg.demo_pg_metadata?fields=pipelineStatuses"
# --8<-- [end:status]

# --8<-- [start:search]
curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/apps/trigger/SearchIndexingApplication
curl -s -H "$AUTH" "http://127.0.0.1:8585/api/v1/search/query?q=*&index=table_search_index&size=1"
# --8<-- [end:search]

# --8<-- [start:remove]
curl -s -X DELETE -H "$AUTH" \
  "http://127.0.0.1:8585/api/v1/services/databaseServices/name/demo_pg?hardDelete=true&recursive=true"
# --8<-- [end:remove]
