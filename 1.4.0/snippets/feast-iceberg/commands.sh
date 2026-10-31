# Commands from docs/guides/feast-iceberg.md. .github/scripts/smoke.sh installs the
# same client into its own environment, then runs the other sections from a
# folder holding a copy of feature_repo/.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up flink-lite
# --8<-- [end:up]

# --8<-- [start:install]
odctl up feast
pip install "feast[duckdb,iceberg,redis,postgres]==0.66.0" pyarrow
# --8<-- [end:install]

# --8<-- [start:catalog-env]
export PYICEBERG_CATALOG__ODCTL__TYPE=rest
export PYICEBERG_CATALOG__ODCTL__URI=http://127.0.0.1:8181
export PYICEBERG_CATALOG__ODCTL__WAREHOUSE=s3://warehouse/
export PYICEBERG_CATALOG__ODCTL__S3__ENDPOINT=http://127.0.0.1:8333
export PYICEBERG_CATALOG__ODCTL__S3__ACCESS_KEY_ID=user
export PYICEBERG_CATALOG__ODCTL__S3__SECRET_ACCESS_KEY=password
export PYICEBERG_CATALOG__ODCTL__S3__PATH_STYLE_ACCESS=true
export PYICEBERG_CATALOG__ODCTL__S3__REGION=us-east-1
# --8<-- [end:catalog-env]

# --8<-- [start:apply-materialize]
feast -c feature_repo apply --skip-source-validation
feast -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"
# --8<-- [end:apply-materialize]

# --8<-- [start:up-airflow]
odctl up airflow
# --8<-- [end:up-airflow]

# --8<-- [start:dag-upload]
docker cp feast_materialize.py airflow:/tmp/feast_materialize.py
docker exec airflow python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").upload_file(
    "/tmp/feast_materialize.py", "airflow", "dags/feast_materialize.py")'
# --8<-- [end:dag-upload]

# --8<-- [start:dag-run]
docker exec airflow airflow dags list | grep feast_materialize
docker exec airflow airflow dags unpause feast_materialize
docker exec airflow airflow dags trigger feast_materialize
docker exec airflow airflow dags list-runs feast_materialize
# --8<-- [end:dag-run]

# --8<-- [start:push-apply]
docker cp push_definitions.py feast-serve:/tmp/feature_repo/push_definitions.py
docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation
# --8<-- [end:push-apply]

# --8<-- [start:push-http]
# Push 0.7 for driver 1001, stamped with the current time.
curl -s -w '%{http_code}\n' -X POST http://127.0.0.1:6566/push \
  -H 'Content-Type: application/json' -d @- <<JSON
{"push_source_name": "driver_push", "allow_registry_cache": false, "to": "online",
 "df": {"driver_id": [1001], "conv_rate": [0.7], "event_timestamp": ["$(date -u +%Y-%m-%dT%H:%M:%S)"]}}
JSON
# --8<-- [end:push-http]

# --8<-- [start:mcp-install]
pip install "mcp>=1.24,<2"
# --8<-- [end:mcp-install]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]

# --8<-- [start:push-read]
curl -s -X POST http://127.0.0.1:6566/get-online-features \
  -H 'Content-Type: application/json' \
  -d '{"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}}'
# --8<-- [end:push-read]
