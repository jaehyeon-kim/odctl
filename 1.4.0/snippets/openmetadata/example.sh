#!/usr/bin/env bash
# Starts metadata, shows AutoPilot's state, registers PostgreSQL as a database
# service and runs a metadata ingestion of the omt database. Then it uploads a
# custom connector, runs its agent, reads its table, counts the searchable
# tables and removes both services and the connector again. Run it in the folder
# that holds .odctl and demo_connector.py, the file of the Add a Custom
# Connector section.
set -euo pipefail

odctl up metadata
om=http://127.0.0.1:8585/api/v1
json() { python3 -c "import json, sys; print($1)"; }

TOKEN=$(curl -s -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin@odctl.io\",\"password\":\"$(printf admin | base64)\"}" \
  "$om/users/login" | json 'json.load(sys.stdin)["accessToken"]')
AUTH="Authorization: Bearer $TOKEN"

echo "autopilot active: $(curl -s -H "$AUTH" "$om/apps/name/AutoPilotApplication?fields=appConfiguration" \
  | json 'json.load(sys.stdin)["appConfiguration"]["active"]')"

# Registers a database service, creates its agent, deploys and triggers it, and
# waits for the run. Usage: ingest <service name> <service JSON>
ingest() {
  local svc pipe state=""
  svc=$(curl -s -X PUT -H "$AUTH" -H 'Content-Type: application/json' -d "$2" \
    "$om/services/databaseServices" | json 'json.load(sys.stdin)["id"]')
  pipe=$(curl -s -X POST -H "$AUTH" -H 'Content-Type: application/json' \
    -d "{\"name\":\"$1_metadata\",\"pipelineType\":\"metadata\",\"service\":{\"id\":\"$svc\",\"type\":\"databaseService\"},\"sourceConfig\":{\"config\":{\"type\":\"DatabaseMetadata\"}},\"airflowConfig\":{\"startDate\":\"2026-01-01T00:00:00.000Z\"}}" \
    "$om/services/ingestionPipelines" | json 'json.load(sys.stdin)["id"]')
  until curl -s -X POST -H "$AUTH" "$om/services/ingestionPipelines/deploy/$pipe" \
    | grep 'has been created' >/dev/null; do sleep 5; done
  # Airflow parses a new DAG file before the trigger works, so the trigger is repeated.
  until curl -s -X POST -H "$AUTH" "$om/services/ingestionPipelines/trigger/$pipe" \
    | grep 'has been triggered' >/dev/null; do sleep 5; done
  until [ "$state" = success ] || [ "$state" = failed ]; do
    sleep 10
    state=$(curl -s -H "$AUTH" \
      "$om/services/ingestionPipelines/name/$1.$1_metadata?fields=pipelineStatuses" \
      | json '(json.load(sys.stdin).get("pipelineStatuses") or [{}])[0].get("pipelineState", "")')
  done
  echo "$1 ingestion: $state"
}

ingest demo_pg '{"name":"demo_pg","serviceType":"Postgres","connection":{"config":{"type":"Postgres","scheme":"postgresql+psycopg2","username":"user","authType":{"password":"password"},"hostPort":"postgres:5432","database":"omt"}}}'

# The container copies the connector from SeaweedFS within about 15 seconds.
docker exec -i openmetadata-ingestion python -c '
import boto3, sys
boto3.client("s3", endpoint_url="http://seaweed:8333").put_object(
    Bucket="openmetadata", Key="connectors/demo_connector.py", Body=sys.stdin.buffer.read())
' < demo_connector.py
until docker exec openmetadata-ingestion test -f /opt/airflow/connectors/demo_connector.py; do sleep 5; done
ingest demo_connector '{"name":"demo_connector","serviceType":"CustomDatabase","connection":{"config":{"type":"CustomDatabase","sourcePythonClass":"demo_connector.DemoSource"}}}'
echo "custom table: $(curl -s -H "$AUTH" "$om/tables/name/demo_connector.demo_db.public.orders" \
  | json 'json.load(sys.stdin)["name"]')"

# The search index fills over a few minutes after it is rebuilt.
curl -s -X POST -H "$AUTH" "$om/apps/trigger/SearchIndexingApplication" >/dev/null
hits=0
until [ "$hits" -gt 100 ]; do
  sleep 5
  hits=$(curl -s -H "$AUTH" "$om/search/query?q=*&index=table_search_index&size=1" \
    | json 'json.load(sys.stdin)["hits"]["total"]["value"]')
done
echo "searchable tables: $hits"

for service in demo_pg demo_connector; do
  curl -s -X DELETE -H "$AUTH" \
    "$om/services/databaseServices/name/$service?hardDelete=true&recursive=true" >/dev/null
done
docker exec openmetadata-ingestion python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").delete_object(
    Bucket="openmetadata", Key="connectors/demo_connector.py")
'
echo "removed demo_pg and demo_connector"
