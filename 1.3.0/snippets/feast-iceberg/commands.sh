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
feast -c feature_repo apply
feast -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"
# --8<-- [end:apply-materialize]

# --8<-- [start:push-apply]
docker cp push_definitions.py feast-serve:/tmp/feature_repo/push_definitions.py
docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation
# --8<-- [end:push-apply]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]

# --8<-- [start:push-read]
curl -s -X POST http://127.0.0.1:6566/get-online-features \
  -H 'Content-Type: application/json' \
  -d '{"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}}'
# --8<-- [end:push-read]
