# Commands from the "Add a Custom Connector" section of docs/guides/openmetadata.md.
# Run them from the folder that holds demo_connector.py, after the login step of
# docs/snippets/openmetadata/commands.sh has set AUTH. .github/scripts/smoke.sh
# runs every section.

# --8<-- [start:upload]
docker exec -i openmetadata-ingestion python -c '
import boto3, sys
boto3.client("s3", endpoint_url="http://seaweed:8333").put_object(
    Bucket="openmetadata", Key="connectors/demo_connector.py", Body=sys.stdin.buffer.read())
' < demo_connector.py
# --8<-- [end:upload]

# --8<-- [start:copied]
docker exec openmetadata-ingestion ls /opt/airflow/connectors
# --8<-- [end:copied]

# --8<-- [start:service]
SVC=$(curl -s -X PUT -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"demo_connector","serviceType":"CustomDatabase","connection":{"config":{"type":"CustomDatabase","sourcePythonClass":"demo_connector.DemoSource"}}}' \
  http://127.0.0.1:8585/api/v1/services/databaseServices \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
# --8<-- [end:service]

# --8<-- [start:agent]
PIPE=$(curl -s -X POST -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"demo_connector_metadata\",\"pipelineType\":\"metadata\",\"service\":{\"id\":\"$SVC\",\"type\":\"databaseService\"},\"sourceConfig\":{\"config\":{\"type\":\"DatabaseMetadata\"}},\"airflowConfig\":{\"startDate\":\"2026-01-01T00:00:00.000Z\"}}" \
  http://127.0.0.1:8585/api/v1/services/ingestionPipelines \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/services/ingestionPipelines/deploy/$PIPE
curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/services/ingestionPipelines/trigger/$PIPE
# --8<-- [end:agent]

# --8<-- [start:status]
curl -s -H "$AUTH" \
  "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/name/demo_connector.demo_connector_metadata?fields=pipelineStatuses"
# --8<-- [end:status]

# --8<-- [start:table]
curl -s -H "$AUTH" \
  "http://127.0.0.1:8585/api/v1/tables/name/demo_connector.demo_db.public.orders?fields=columns"
# --8<-- [end:table]

# --8<-- [start:change]
sed -i.bak 's/name="orders"/name="orders_v2"/' demo_connector.py
# --8<-- [end:change]

# --8<-- [start:copied-change]
docker exec openmetadata-ingestion grep -c orders_v2 /opt/airflow/connectors/demo_connector.py
# --8<-- [end:copied-change]

# --8<-- [start:retrigger]
curl -s -X POST -H "$AUTH" http://127.0.0.1:8585/api/v1/services/ingestionPipelines/trigger/$PIPE
# --8<-- [end:retrigger]

# --8<-- [start:changed-table]
curl -s -H "$AUTH" \
  "http://127.0.0.1:8585/api/v1/tables/name/demo_connector.demo_db.public.orders_v2"
# --8<-- [end:changed-table]
