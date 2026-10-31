# Commands from docs/guides/lineage.md. .github/scripts/smoke.sh runs each section.

# smoke.sh does not run the up sections or airflow-env: the e2e workflow starts
# each profile itself, and sets AIRFLOW_OPENLINEAGE_TRANSPORT in its shell rather
# than editing .env.
# --8<-- [start:up]
odctl up lineage
# --8<-- [end:up]

# --8<-- [start:send]
RUN_ID=a1b2c3d4-0000-4000-8000-000000000001
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

for event in START COMPLETE; do
  curl -s -X POST http://127.0.0.1:5002/api/v1/lineage \
    -H 'Content-Type: application/json' \
    -d "{\"eventType\":\"$event\",\"eventTime\":\"$NOW\",
         \"producer\":\"demo\",
         \"run\":{\"runId\":\"$RUN_ID\"},
         \"job\":{\"namespace\":\"demo\",\"name\":\"demo-job\"},
         \"inputs\":[{\"namespace\":\"demo\",\"name\":\"raw-orders\"}],
         \"outputs\":[{\"namespace\":\"demo\",\"name\":\"demo-dataset\"}]}"
done
# --8<-- [end:send]

# --8<-- [start:read]
curl http://127.0.0.1:5002/api/v1/namespaces
curl http://127.0.0.1:5002/api/v1/namespaces/demo/jobs/demo-job
curl http://127.0.0.1:5002/api/v1/namespaces/demo/datasets/demo-dataset
# --8<-- [end:read]

# --8<-- [start:airflow-env]
sed -i.bak "s|^AIRFLOW_OPENLINEAGE_TRANSPORT=.*|AIRFLOW_OPENLINEAGE_TRANSPORT='{\"type\": \"http\", \"url\": \"http://marquez-api:5000\"}'|" .odctl/.env
# --8<-- [end:airflow-env]

# --8<-- [start:airflow-up]
odctl up airflow
# --8<-- [end:airflow-up]

# --8<-- [start:airflow-connection]
docker exec airflow airflow connections add odctl_postgres \
  --conn-type postgres --conn-host postgres --conn-login user --conn-password password \
  --conn-schema odctl --conn-port 5432
# --8<-- [end:airflow-connection]

# --8<-- [start:airflow-upload]
docker cp lineage_orders.py airflow:/tmp/lineage_orders.py
docker exec airflow python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").upload_file(
    "/tmp/lineage_orders.py", "airflow", "dags/lineage_orders.py")'
# --8<-- [end:airflow-upload]

# --8<-- [start:airflow-run]
docker exec airflow airflow dags list | grep lineage_orders
docker exec airflow airflow dags unpause lineage_orders
docker exec airflow airflow dags trigger lineage_orders
# --8<-- [end:airflow-run]

# --8<-- [start:airflow-read]
# The jobs of the namespace default, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/default/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
# --8<-- [end:airflow-read]

# --8<-- [start:spark-up]
odctl up spark-lite
# --8<-- [end:spark-up]

# --8<-- [start:spark-submit]
docker cp orders_job.py spark-master:/tmp/orders_job.py
# Submit the job with the OpenLineage listener sending to marquez-api.
docker exec spark-master /opt/spark/bin/spark-submit \
  --driver-class-path '/mnt/shared-deps/spark/openlineage.jar:/mnt/shared-deps/shared/*:/mnt/shared-deps/spark/*' \
  --conf spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener \
  --conf spark.openlineage.transport.type=http \
  --conf spark.openlineage.transport.url=http://marquez-api:5000 \
  --conf spark.openlineage.namespace=odctl \
  /tmp/orders_job.py
# --8<-- [end:spark-submit]

# --8<-- [start:spark-read]
# The jobs of the namespace odctl, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/odctl/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
# --8<-- [end:spark-read]

# --8<-- [start:feast-apply]
docker exec airflow mkdir -p /tmp/lineage_repo
docker cp lineage_repo/feature_store.yaml airflow:/tmp/lineage_repo/feature_store.yaml
docker cp feature_repo/definitions.py airflow:/tmp/lineage_repo/definitions.py
docker exec airflow feast -c /tmp/lineage_repo apply --skip-source-validation
# --8<-- [end:feast-apply]

# --8<-- [start:feast-read]
# The jobs of the namespace lineage_demo, the name of the Feast project, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/lineage_demo/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
# --8<-- [end:feast-read]
