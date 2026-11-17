#!/usr/bin/env bash
# Starts feast and flink-lite, builds an Iceberg table of driver features,
# registers a feature view over it, materialises it into Valkey and reads it
# back, then pushes a value to the feature server over HTTP and through Flink
# SQL, reads that back, and lists the feature server's MCP tools. Run it in an
# environment with "feast[duckdb,iceberg,redis,postgres]==0.66.0", pyarrow and
# "mcp>=1.24,<2" installed.
set -euo pipefail

odctl up feast flink-lite

export PYICEBERG_CATALOG__ODCTL__TYPE=rest
export PYICEBERG_CATALOG__ODCTL__URI=http://127.0.0.1:8181
export PYICEBERG_CATALOG__ODCTL__WAREHOUSE=s3://warehouse/
export PYICEBERG_CATALOG__ODCTL__S3__ENDPOINT=http://127.0.0.1:8333
export PYICEBERG_CATALOG__ODCTL__S3__ACCESS_KEY_ID=user
export PYICEBERG_CATALOG__ODCTL__S3__SECRET_ACCESS_KEY=password
export PYICEBERG_CATALOG__ODCTL__S3__PATH_STYLE_ACCESS=true
export PYICEBERG_CATALOG__ODCTL__S3__REGION=us-east-1

python - <<'PY'
import datetime, pyarrow as pa
from pyiceberg.catalog import load_catalog

cat = load_catalog("odctl")
cat.create_namespace_if_not_exists("demo")
schema = pa.schema([
    pa.field("driver_id", pa.int64(), nullable=False),
    pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("conv_rate", pa.float32(), nullable=False),
])
t = cat.create_table_if_not_exists("demo.driver_stats", schema=schema)
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
t.append(pa.Table.from_pydict({
    "driver_id": [1001, 1002],
    "event_timestamp": [now - datetime.timedelta(hours=1)] * 2,
    "conv_rate": [0.5, 0.75],
}, schema=schema))
PY

mkdir -p feature_repo
cat > feature_repo/feature_store.yaml <<'YAML'
project: demo
provider: local
registry:
  registry_type: sql
  path: postgresql+psycopg://user:password@127.0.0.1:5432/feast
offline_store:
  type: duckdb
online_store:
  type: redis
  connection_string: "127.0.0.1:6379,username=user,password=password"
entity_key_serialization_version: 3
YAML
cat > feature_repo/definitions.py <<'PY'
from datetime import timedelta
from feast import Entity, FeatureView, Field
from feast.types import Float32
from feast.value_type import ValueType
from feast.infra.data_sources.contrib.iceberg_catalog.iceberg_source import IcebergSource

driver = Entity(name="driver", join_keys=["driver_id"], value_type=ValueType.INT64)
src = IcebergSource(
    warehouse="", namespace="demo", table="driver_stats",
    catalog_type="rest", catalog_name="odctl",
    timestamp_field="event_timestamp",
)
fv = FeatureView(
    name="driver_stats", entities=[driver], ttl=timedelta(days=365),
    schema=[Field(name="conv_rate", dtype=Float32)], source=src, online=True,
)
PY

feast -c feature_repo apply --skip-source-validation
feast -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"

python - <<'PY'
from feast import FeatureStore

fs = FeatureStore(repo_path="feature_repo")
print(fs.get_online_features(
    features=["driver_stats:conv_rate"],
    entity_rows=[{"driver_id": 1001}, {"driver_id": 1002}],
).to_dict())
PY

# The push source goes into the feature server's own repository.
cat > push_definitions.py <<'PY'
from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, PushSource
from feast.types import Float32, Int64
from feast.value_type import ValueType

driver = Entity(name="driver", join_keys=["driver_id"], value_type=ValueType.INT64)
# Nothing reads this file. A push source needs a batch source behind it.
batch = FileSource(path="/tmp/driver_stats.parquet", timestamp_field="event_timestamp")
push = PushSource(name="driver_push", batch_source=batch)
driver_pushed = FeatureView(
    name="driver_pushed",
    entities=[driver],
    ttl=timedelta(days=1),
    schema=[Field(name="driver_id", dtype=Int64), Field(name="conv_rate", dtype=Float32)],
    source=push,
    online=True,
)
PY
docker cp push_definitions.py feast-serve:/tmp/feature_repo/push_definitions.py
docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation

# Push 0.7 for driver 1001 over HTTP, stamped with the current time.
curl -s -w '%{http_code}\n' -X POST http://127.0.0.1:6566/push \
  -H 'Content-Type: application/json' -d @- <<JSON
{"push_source_name": "driver_push", "allow_registry_cache": false, "to": "online",
 "df": {"driver_id": [1001], "conv_rate": [0.7], "event_timestamp": ["$(date -u +%Y-%m-%dT%H:%M:%S)"]}}
JSON

# Flink pushes 0.9 for the same driver, with a newer timestamp.
docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<'SQL' | grep -E 'ERROR|Complete'
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
CREATE TABLE feast_push (
  push_source_name STRING,
  df ROW<driver_id ARRAY<BIGINT>, conv_rate ARRAY<DOUBLE>, event_timestamp ARRAY<TIMESTAMP_LTZ(3)>>,
  allow_registry_cache BOOLEAN
) WITH (
  'connector' = 'http-async-sink',
  'url' = 'http://feast-serve:6566/push',
  'format' = 'json',
  'http.sink.writer.request.mode' = 'single',
  'http.sink.header.Content-Type' = 'application/json'
);
INSERT INTO feast_push SELECT 'driver_push', ROW(ARRAY[CAST(1001 AS BIGINT)], ARRAY[CAST(0.9 AS DOUBLE)], ARRAY[CURRENT_TIMESTAMP]), FALSE;
SQL

# The feature server can take up to a minute to see a new feature view.
tries=0
until curl -s -X POST http://127.0.0.1:6566/get-online-features \
    -H 'Content-Type: application/json' \
    -d '{"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}}' \
    | grep 0.8999999761581421; do
  tries=$((tries + 1))
  [ "$tries" -lt 24 ] || { echo "Flink's push did not arrive. Look for 'Http Sink failed to write' in the TaskManager log." >&2; exit 1; }
  sleep 5
done

python - <<'PY'
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client("http://127.0.0.1:6566/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool in (await session.list_tools()).tools:
                print(tool.name)
            result = await session.call_tool(
                "get_online_features_get_online_features_post",
                {"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}},
            )
            if result.isError:
                return result.content[0].text
            reply = json.loads(result.content[0].text)
            names = reply["metadata"]["feature_names"]
            print(reply["results"][names.index("conv_rate")]["values"])


error = asyncio.run(main())
if error:
    raise SystemExit(error)
PY
