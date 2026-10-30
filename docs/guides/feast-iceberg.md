# Feast with Iceberg

Feast is a feature store: it keeps the definitions of a model's input features and serves their values. The offline store holds the history of each feature, for training. The online store holds each entity's latest value, for serving a prediction quickly. Materialising copies values from the offline store to the online store. The `feast` profile runs the Feast UI and the online feature server. Feast stores no feature values of its own. Feature definitions live in a SQL registry in PostgreSQL, offline values come from Iceberg tables through the REST catalog, and online values are served from Valkey. You run `feast apply` and the other client commands from your own environment. The end-to-end tests run the steps below on every release.

This guide builds on [Ingest into Iceberg](iceberg-ingestion.md), which writes Iceberg tables through the catalog, [Flink SQL](flink-sql.md), whose SQL client the Flink push uses, and [Airflow DAGs from S3](airflow-dags.md), which uploads and runs a DAG. Follow the arrows from the `feast` CLI on the left: definitions go to the registry, and values go from Iceberg to Valkey. An Airflow DAG at the bottom centre also materialises into Valkey, on a schedule. A client at the bottom right can also push a value through the feature server into Valkey.

![The feast CLI writes definitions to the registry in PostgreSQL, reads offline values from Iceberg and materialises them into Valkey; an Airflow DAG also materialises into Valkey; the Feast UI and feature server load the repository from SeaweedFS and the feature server reads and writes Valkey; a client pushes values to the feature server's /push route](../assets/diagrams/path-feast.png)

Start the profile and install the client, with the extras that read Iceberg, PostgreSQL and Valkey:

```bash title="docs/snippets/feast-iceberg/commands.sh:install"
odctl up feast
pip install "feast[duckdb,iceberg,redis,postgres]==0.66.0" pyarrow
```

| Endpoint | Address |
| --- | --- |
| Feast UI | `http://127.0.0.1:8890` |
| Feature server from the host | `http://127.0.0.1:6566` |
| Feature server inside the `odctl` network | `http://feast-serve:6566` |
| MCP endpoint from the host | `http://127.0.0.1:6566/mcp` |
| Registry | the `feast` database on PostgreSQL |

## Point the Clients at the Stack

PyIceberg, which Feast uses to read Iceberg, takes its catalog settings from the environment. Run these in the shell where you run the next steps:

```bash title="docs/snippets/feast-iceberg/commands.sh:catalog-env"
export PYICEBERG_CATALOG__ODCTL__TYPE=rest
export PYICEBERG_CATALOG__ODCTL__URI=http://127.0.0.1:8181
export PYICEBERG_CATALOG__ODCTL__WAREHOUSE=s3://warehouse/
export PYICEBERG_CATALOG__ODCTL__S3__ENDPOINT=http://127.0.0.1:8333
export PYICEBERG_CATALOG__ODCTL__S3__ACCESS_KEY_ID=user
export PYICEBERG_CATALOG__ODCTL__S3__SECRET_ACCESS_KEY=password
export PYICEBERG_CATALOG__ODCTL__S3__PATH_STYLE_ACCESS=true
export PYICEBERG_CATALOG__ODCTL__S3__REGION=us-east-1
```

## Create an Iceberg Table

Save this code as `create_table.py` and run it with `python create_table.py`. It creates `demo.driver_stats` if it does not exist and writes one hour-old row for each of two drivers:

```python title="docs/snippets/feast-iceberg/steps.py:create-table"
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
```

## Define the Feature Repository

A feature repository is a folder of configuration and definitions. Save this file as `feature_repo/feature_store.yaml`. It names the registry, the offline store and the online store:

```yaml title="docs/snippets/feast-iceberg/feature_repo/feature_store.yaml"
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
```

Save the definitions as `feature_repo/definitions.py`. They declare the entity `driver` and the feature view `driver_stats` over the Iceberg table:

```python title="docs/snippets/feast-iceberg/feature_repo/definitions.py"
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
```

Pass `catalog_name="odctl"`, so that PyIceberg reads the `PYICEBERG_CATALOG__ODCTL__*` variables. Pass `warehouse=""`, so that PyIceberg takes the warehouse from `PYICEBERG_CATALOG__ODCTL__WAREHOUSE`. The source has no `endpoint`, so the registry stores no catalog address, and PyIceberg takes it from `PYICEBERG_CATALOG__ODCTL__URI`. Each program that reads the registry therefore uses its own address: `http://127.0.0.1:8181` in your shell and `http://catalog:8181` in the Airflow container, set today in `x-airflow-common` of `.odctl/compose-orch.yml`, where an edit can change it. The entity names its `value_type`, so that `apply` need not read the table to find the type of `driver_id`.

## Register and Materialise

Run these from the folder that holds `feature_repo`. `apply` writes the definitions to the registry, and `materialize-incremental` copies the latest values into Valkey. `--skip-source-validation` stops `apply` from checking the Iceberg source with Feast's own catalog client, which would need the catalog address that the source leaves out:

```bash title="docs/snippets/feast-iceberg/commands.sh:apply-materialize"
feast -c feature_repo apply --skip-source-validation
feast -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"
```

`apply` prints `Applying changes for project demo` and `Deploying infrastructure for driver_stats`, and `materialize-incremental` names the feature view and the time range it copied.

### On a Schedule

The DAG uses the table and the feature view from the steps above, so run them first. Materialising by hand copies only the values that exist at that moment. An Airflow DAG can run `materialize_incremental` on a schedule. `materialize_incremental` is the method behind `feast materialize-incremental`. It copies the rows whose `event_timestamp` falls between the end of the previous materialisation and `end_date`, so a row written later with an older timestamp is not copied. The `airflow` image already has the Feast client, so the DAG installs nothing. It builds the feature store in code from three settings: the registry address in `FEAST_REGISTRY`, which the Airflow container sets; the DuckDB offline store; and the Valkey online store at the container address `valkey:6379`. Save it as `feast_materialize.py`:

```python title="docs/snippets/feast-iceberg/feast_materialize.py"
from datetime import datetime, timezone

from airflow.sdk import dag, task


@dag(
    dag_id="feast_materialize",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule="@hourly",
    catchup=False,
)
def feast_materialize():
    @task
    def materialize():
        # Imported here so that parsing the file does not load Feast.
        import os

        from feast import FeatureStore, RepoConfig

        store = FeatureStore(config=RepoConfig(
            project="demo",
            provider="local",
            registry={"registry_type": "sql", "path": os.environ["FEAST_REGISTRY"]},
            offline_store={"type": "duckdb"},
            online_store={
                "type": "redis",
                "connection_string": "valkey:6379,username=user,password=password",
            },
            entity_key_serialization_version=3,
        ))
        store.materialize_incremental(end_date=datetime.now(timezone.utc))

    materialize()


feast_materialize()
```

`schedule="@hourly"` runs the DAG at the start of each hour. `catchup=False` skips the hours missed while Airflow was stopped, because one incremental run covers them. Start Airflow beside Feast:

```bash title="docs/snippets/feast-iceberg/commands.sh:up-airflow"
odctl up airflow
```

Copy the DAG into the Airflow container and upload it to `s3://airflow/dags`, as [Airflow DAGs from S3](airflow-dags.md#upload-a-dag) does:

```bash title="docs/snippets/feast-iceberg/commands.sh:dag-upload"
docker cp feast_materialize.py airflow:/tmp/feast_materialize.py
docker exec airflow python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").upload_file(
    "/tmp/feast_materialize.py", "airflow", "dags/feast_materialize.py")'
```

Airflow reads the bucket every 15 seconds, so the DAG appears in its list a short time after the upload. To give the next run a value to copy, save this code as `append.py` and run it with `python append.py` in the shell where you set the catalog variables. It appends the value 0.6 for driver 1001, with the current time, to the Iceberg table:

```python title="docs/snippets/feast-iceberg/steps.py:append"
import datetime, pyarrow as pa
from pyiceberg.catalog import load_catalog

t = load_catalog("odctl").load_table("demo.driver_stats")
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
t.append(pa.Table.from_pydict({
    "driver_id": [1001],
    "event_timestamp": [now],
    "conv_rate": [0.6],
}, schema=t.schema().as_arrow()))
```

Then unpause the DAG and trigger a run. Repeat the first command until it prints the DAG's line. Before that, `unpause` prints `No paused DAGs were found` and changes nothing, and `trigger` and `list-runs` fail. Unpausing also starts one scheduled run, for the latest hour that has ended, so the last command can list two runs:

```bash title="docs/snippets/feast-iceberg/commands.sh:dag-run"
docker exec airflow airflow dags list | grep feast_materialize
docker exec airflow airflow dags unpause feast_materialize
docker exec airflow airflow dags trigger feast_materialize
docker exec airflow airflow dags list-runs feast_materialize
```

Run the last command again until each run shows `success`. Run the read from [Read the Features](#read-the-features) below. After the DAG run it prints `{'driver_id': [1001, 1002], 'conv_rate': [0.6000000238418579, 0.75]}`, because the DAG copied 0.6, which is a 32-bit float, into Valkey.

![Airflow showing the feast_materialize DAG and its two successful runs](../images/feast-materialise.png){ .screenshot }

## Read the Features

`FeatureStore(repo_path="feature_repo").get_historical_features(...)` takes a point-in-time join from Iceberg through DuckDB, for training. This reads the materialised values from Valkey instead, as a model server would:

```python title="docs/snippets/feast-iceberg/steps.py:read"
from feast import FeatureStore

fs = FeatureStore(repo_path="feature_repo")
print(fs.get_online_features(
    features=["driver_stats:conv_rate"],
    entity_rows=[{"driver_id": 1001}, {"driver_id": 1002}],
).to_dict())
```

It prints `{'driver_id': [1001, 1002], 'conv_rate': [0.5, 0.75]}`. Driver 1001 reads `0.6000000238418579` instead if you ran the DAG in [On a Schedule](#on-a-schedule).

## Serve from the Stack

The UI at `http://127.0.0.1:8890` and the online feature server at `http://127.0.0.1:6566` load their repository from `s3://feast/repo`. To serve your features, upload the repository there with container addresses in its `feature_store.yaml`: `postgres:5432` and `valkey:6379`. The definitions need no change, because the services take the catalog address from `PYICEBERG_CATALOG__ODCTL__URI`, which is `http://catalog:8181` in `x-feast-env` of `.odctl/compose-mlops.yml` today. The services check that prefix every 15 seconds and restart Feast when it changes. The interval is set today by `time.sleep(15)` in `x-feast-repo-sync` in `.odctl/compose-mlops.yml`. Two other profiles also read their code from a bucket; [How It Works](../how-it-works.md#where-data-lives) compares the three.

Once the repository is uploaded, the UI lists the project and its feature views:

![Feast UI showing the driver_stats feature view](../images/feast-ui.png){ .screenshot }

## Push Features

A push source lets a client write a feature value straight to the online store, through the feature server's `/push` endpoint, instead of materialising it. A client can be `curl`, a Flink SQL job, or a small Python process that reads Kafka and calls `FeatureStore.push` with `PushMode.ONLINE`. That mode writes to the online store only, as `"to": "online"` does over HTTP. [Keep Messages Longer](kafka.md#keep-messages-longer) says how long Kafka keeps a stream for such a process to replay. The slower route writes the stream to Iceberg with Flink and runs `feast materialize-incremental` on a schedule, as [On a Schedule](#on-a-schedule) shows, so a value reaches the online store only after the next run.

Feast needs a push source before it accepts a push. The feature server serves the project `odctl`, which its own `feature_store.yaml` names, so the definitions are applied from inside the `feast-serve` container. Save these definitions as `push_definitions.py`. They declare the push source `driver_push` and the feature view `driver_pushed`:

```python title="docs/snippets/feast-iceberg/push_definitions.py"
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
```

Copy the definitions into the Feast container and apply them. `--skip-source-validation` stops Feast from looking for the file behind the batch source:

```bash title="docs/snippets/feast-iceberg/commands.sh:push-apply"
docker cp push_definitions.py feast-serve:/tmp/feature_repo/push_definitions.py
docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation
```

`apply` prints `Applying changes for project odctl` and `Deploying infrastructure for driver_pushed`.

### Over HTTP

This sends the value 0.7 for driver 1001 to `/push`. The body names the push source and holds `df`, a table of columns in which each field is an array, and `"to": "online"` writes to the online store only:

```bash title="docs/snippets/feast-iceberg/commands.sh:push-http"
# Push 0.7 for driver 1001, stamped with the current time.
curl -s -w '%{http_code}\n' -X POST http://127.0.0.1:6566/push \
  -H 'Content-Type: application/json' -d @- <<JSON
{"push_source_name": "driver_push", "allow_registry_cache": false, "to": "online",
 "df": {"driver_id": [1001], "conv_rate": [0.7], "event_timestamp": ["$(date -u +%Y-%m-%dT%H:%M:%S)"]}}
JSON
```

It prints `200`. Feast caches its registry for up to a minute after `apply`, and `allow_registry_cache` set to `false` makes the push read the registry again, so it works at once. The timestamp must be new: a push with the same `event_timestamp` as the stored value does not replace it. Read the value back from the feature server:

```bash title="docs/snippets/feast-iceberg/commands.sh:push-read"
curl -s -X POST http://127.0.0.1:6566/get-online-features \
  -H 'Content-Type: application/json' \
  -d '{"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}}'
```

The answer holds `0.699999988079071` for `conv_rate`, which is 0.7 as a 32-bit float. The read also uses the cached registry, so right after `apply` it can answer that the feature view does not exist. Run it again after a minute.

### From Flink SQL

Flink's HTTP connector sends rows to a URL, so a Flink SQL job can push each value it computes. Start Flink beside Feast:

```bash title="docs/snippets/feast-iceberg/commands.sh:up"
odctl up flink-lite
```

Open the SQL client:

```bash title="docs/snippets/feast-iceberg/commands.sh:sql-client"
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
```

Then run these statements, which push the value 0.9 for driver 1001:

```sql title="docs/snippets/feast-iceberg/steps.sql:feast-push"
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
```

The connector is `http-async-sink`. Its default sends rows in batches as one JSON array. Feast's `/push` takes one JSON object, so `http.sink.writer.request.mode` is `single`, which sends one request for each row. The sink sends no `Content-Type` header, and Feast answers 422 without one, so `http.sink.header.Content-Type` sets it. The column names are the field names of the request body, and each field of `df` holds an array, as under Over HTTP. `allow_registry_cache` is `FALSE` so that the push reads the registry again, as under Over HTTP. The statement uses `CURRENT_TIMESTAMP` so that the timestamp is newer than the one the HTTP push stored.

The Flink job finishes and prints `Complete execution of the SQL update statement.` even when Feast rejects the request. The failure is only in the TaskManager log as `Http Sink failed to write`. Run the read from Over HTTP again to check the push. The answer now holds `0.8999999761581421` for `conv_rate`, which is 0.9 as a 32-bit float.

## Connect an MCP Client

MCP, the Model Context Protocol, lets an AI agent discover and call the tools of a server. `feast-serve` serves an MCP endpoint at `http://127.0.0.1:6566/mcp`, and each route of the feature server is a tool. The bundled repository sets `mcp_transport: http`, which is Streamable HTTP: the client sends each request as an HTTP POST to the one `/mcp` address. The MCP specification of 2025-03-26 put it in place of HTTP with server-sent events. odctl does not install an MCP client, so install the Python one in your environment:

```bash title="docs/snippets/feast-iceberg/commands.sh:mcp-install"
pip install "mcp>=1.24,<2"
```

Save this code as `mcp_client.py` and run it with `python mcp_client.py`. It lists the tools, then calls the tool for `/get-online-features` to read `driver_pushed:conv_rate`, the value pushed above. Run [Push Features](#push-features) first: without `driver_pushed`, the call fails and the script prints Feast's error, which names the missing feature view.

```python title="docs/snippets/feast-iceberg/mcp_client.py"
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
```

It prints the name of each tool, such as `push_push_post`, which is the route function, its path and its HTTP method, and then the value as `[0.8999999761581421]`. It prints `[0.699999988079071]` if you pushed over HTTP only.

## From Another Container

Inside the [`odctl` network](../how-it-works.md#how-you-reach-a-service), the feature server is `http://feast-serve:6566`. A repository for the services uses `postgres:5432` for the registry and `valkey:6379` for the online store, and its Iceberg source names no address.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace, in an environment with the Feast and MCP clients installed as above. It writes the repository files into `feature_repo` in that folder, and appends two rows to `demo.driver_stats` on each run:

```bash title="docs/snippets/feast-iceberg/example.sh"
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
```

It prints `{'driver_id': [1001, 1002], 'conv_rate': [0.5, 0.75]}`, the status `200` of the HTTP push and the feature server's answer with `0.8999999761581421`. Then it prints the name of each MCP tool and the value `[0.8999999761581421]`. Driver 1001 reads `0.6000000238418579` in the first value instead if you ran the DAG in [On a Schedule](#on-a-schedule).
