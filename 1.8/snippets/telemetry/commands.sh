# Commands from docs/guides/telemetry.md. .github/scripts/smoke.sh runs the
# send-metric and container sections.

# smoke.sh does not run the up sections or drift-env, because the e2e workflow
# starts each profile itself and sets _AIRFLOW_PIP_DEPS in its shell rather than
# editing .env; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up telemetry kafka-lite flink-lite
# --8<-- [end:up]

# --8<-- [start:send-metric]
ts=$(python3 -c "import time;print(int(time.time()*1e9))")
cat > /tmp/otlp.json <<JSON
{"resourceMetrics":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"demo"}}]},
"scopeMetrics":[{"scope":{"name":"demo"},"metrics":[{"name":"demo_total","unit":"1",
"sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[
{"asDouble":42,"timeUnixNano":"${ts}","startTimeUnixNano":"${ts}","attributes":[]}]}}]}]}]}
JSON
curl -X POST -H "Content-Type: application/json" --data-binary @/tmp/otlp.json \
  http://127.0.0.1:4318/v1/metrics
curl "http://127.0.0.1:19090/api/v1/query?query=demo_total"
# --8<-- [end:send-metric]

# --8<-- [start:container]
# An empty batch is enough to check the address. The collector answers 200.
docker run --rm --network odctl curlimages/curl:8.17.0 -s -o /dev/null -w "%{http_code}\n" \
  -H "Content-Type: application/json" -d '{}' http://otel-lgtm:4318/v1/traces
# --8<-- [end:container]

# --8<-- [start:alert-rules]
# Title of each alert rule that Grafana loaded.
curl -s -u user:password http://127.0.0.1:3004/api/v1/provisioning/alert-rules \
  | python3 -c '
import json, sys
for rule in json.load(sys.stdin):
    print(rule["title"])'
# --8<-- [end:alert-rules]

# --8<-- [start:drift-env]
sed -i.bak 's|^_AIRFLOW_PIP_DEPS=.*|_AIRFLOW_PIP_DEPS="evidently==0.7.23"|' .odctl/.env
# --8<-- [end:drift-env]

# --8<-- [start:drift-up]
odctl up airflow
# --8<-- [end:drift-up]

# --8<-- [start:drift-upload]
docker cp drift_check.py airflow:/tmp/drift_check.py
docker exec airflow python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").upload_file(
    "/tmp/drift_check.py", "airflow", "dags/drift_check.py")'
# --8<-- [end:drift-upload]

# --8<-- [start:drift-run]
docker exec airflow airflow dags list | grep drift_check
docker exec airflow airflow dags unpause drift_check
docker exec airflow airflow dags trigger drift_check --run-id drifted
# --8<-- [end:drift-run]

# --8<-- [start:drift-score]
# Distance each run printed, from its task log.
docker exec airflow sh -c 'cd /opt/airflow/logs/dag_id=drift_check && grep -o "Wasserstein distance[^\"]*" run_id=*/task_id=check_drift/attempt=1.log'
# --8<-- [end:drift-score]

# --8<-- [start:alert-state]
# Alerts that are firing, with the DAG each names.
curl -s -u user:password http://127.0.0.1:3004/api/prometheus/grafana/api/v1/alerts \
  | python3 -c '
import json, sys
for alert in json.load(sys.stdin)["data"]["alerts"]:
    if alert["state"] == "Alerting":
        print(alert["labels"]["alertname"], alert["labels"].get("dag_id", ""), alert["state"])'
# --8<-- [end:alert-state]

# --8<-- [start:drift-steady]
docker exec airflow airflow dags trigger drift_check --run-id steady --conf '{"shift": 0}'
# --8<-- [end:drift-steady]

# --8<-- [start:add-rule]
cp token_budget.yaml .odctl/grafana/alerting/
odctl restart telemetry
# --8<-- [end:add-rule]
