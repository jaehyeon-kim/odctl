# OpenLineage and Marquez

The `lineage` profile runs Marquez: an API that receives OpenLineage events and keeps jobs, runs and datasets on PostgreSQL, and a web UI that draws the lineage graph. OpenLineage is an open standard for events that say which job read and wrote which datasets in each run. Anything that sends OpenLineage events over HTTP can report to Marquez. Airflow, a Spark job and `feast apply` can each send them, and a section below sets up each one. The end-to-end tests run the commands below on every release, except the `up` commands and the `.env` edit: the workflow starts each profile itself and sets the transport in its shell.

This guide builds on [Getting Started](../getting-started.md).

Your job, Airflow, Spark and Feast send their events to `marquez-api`, and `marquez-web` reads the API to draw the graph:

![Your job, Airflow, spark-submit with the OpenLineage listener and feast apply send OpenLineage events to marquez-api, which keeps them in PostgreSQL; marquez-web reads the API to draw the graph](../assets/diagrams/path-lineage.png)

Start the profile:

```bash title="docs/snippets/lineage/commands.sh:up"
odctl up lineage
```

| Endpoint | Address |
| --- | --- |
| Marquez API from the host | `http://127.0.0.1:5002` |
| Marquez API inside the `odctl` network | `http://marquez-api:5000` |
| Lineage graph UI | `http://127.0.0.1:3003` |

## Send OpenLineage Events

A run is reported as a `START` event and a `COMPLETE` event with the same run id. The job reads one dataset and writes another:

```bash title="docs/snippets/lineage/commands.sh:send"
RUN_ID=a1b2c3d4-0000-4000-8000-000000000001
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

for event in START COMPLETE; do
  curl -X POST http://127.0.0.1:5002/api/v1/lineage \
    -H 'Content-Type: application/json' \
    -d "{\"eventType\":\"$event\",\"eventTime\":\"$NOW\",
         \"producer\":\"demo\",
         \"run\":{\"runId\":\"$RUN_ID\"},
         \"job\":{\"namespace\":\"demo\",\"name\":\"demo-job\"},
         \"inputs\":[{\"namespace\":\"demo\",\"name\":\"raw-orders\"}],
         \"outputs\":[{\"namespace\":\"demo\",\"name\":\"demo-dataset\"}]}"
done
```

The run id is a UUID, as OpenLineage requires. Each request prints nothing when Marquez accepts the event.

## Read the Lineage Back

These read the namespaces, the job and the output dataset back from the API:

```bash title="docs/snippets/lineage/commands.sh:read"
curl http://127.0.0.1:5002/api/v1/namespaces
curl http://127.0.0.1:5002/api/v1/namespaces/demo/jobs/demo-job
curl http://127.0.0.1:5002/api/v1/namespaces/demo/datasets/demo-dataset
```

Marquez writes the job, the run and the dataset from the events, so all three read back. The first command lists the namespaces, which include `demo`. The second returns the job `demo-job` as JSON, with `raw-orders` among its inputs, `demo-dataset` among its outputs and a `latestRun` in state `COMPLETED`. The third returns the dataset. The UI shows them under the `demo` namespace.

The UI draws the job between the datasets it read and wrote:

![Marquez lineage graph of demo-job between two datasets](../images/marquez.png){ .screenshot }

## Lineage from Airflow

Airflow's OpenLineage provider is installed in the `airflow` image. It sends a `START` event and a `COMPLETE` event for each DAG run and each task, and for a SQL task it reads the tables from the SQL. It sends events only when it has a transport, which is the setting that says where to send them. odctl leaves the transport empty, so with no change Airflow sends nothing and logs no error. This section builds on [Airflow DAGs from S3](airflow-dags.md), which explains how to upload and run a DAG.

Set the transport in the `.env` key `AIRFLOW_OPENLINEAGE_TRANSPORT`. Its value is JSON: `type` is `http`, and `url` is the address of `marquez-api` inside the `odctl` network, from the table at the top of this page. `sed -i.bak` works with both GNU and macOS `sed`, and keeps the original as `.env.bak`. Run this in the folder that holds your `.odctl` workspace, then start Airflow:

```bash title="docs/snippets/lineage/commands.sh:airflow-env"
sed -i.bak "s|^AIRFLOW_OPENLINEAGE_TRANSPORT=.*|AIRFLOW_OPENLINEAGE_TRANSPORT='{\"type\": \"http\", \"url\": \"http://marquez-api:5000\"}'|" .odctl/.env
```

```bash title="docs/snippets/lineage/commands.sh:airflow-up"
odctl up airflow
```

If Airflow is already running, run `odctl recreate airflow` instead, because a restart does not read `.env` again, as [Apply a Change](../how-it-works.md#apply-a-change) explains.

The DAG has two tasks that run SQL on the `odctl` database of the `postgres` service. The first creates `raw_orders`, and the second builds `daily_orders` from it. Both tables are in the `dev` schema. The `odctl` database looks in `cdc` first, so the SQL names `dev`. Save it as `lineage_orders.py`:

```python title="docs/snippets/lineage/lineage_orders.py" hl_lines="25 26"
import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sdk import DAG

with DAG(
    dag_id="lineage_orders",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
):
    seed_raw_orders = SQLExecuteQueryOperator(
        task_id="seed_raw_orders",
        conn_id="odctl_postgres",
        sql=[
            "DROP TABLE IF EXISTS dev.raw_orders",
            "CREATE TABLE dev.raw_orders AS SELECT * FROM "
            "(VALUES ('a', 5.0), ('a', 10.0), ('b', 7.5)) AS t(supplier, price)",
        ],
    )
    build_daily_orders = SQLExecuteQueryOperator(
        task_id="build_daily_orders",
        conn_id="odctl_postgres",
        sql=[
            "DROP TABLE IF EXISTS dev.daily_orders",
            "CREATE TABLE dev.daily_orders AS "
            "SELECT supplier, sum(price) AS total FROM dev.raw_orders GROUP BY supplier",
        ],
    )
    seed_raw_orders >> build_daily_orders
```

The provider parses each statement. The highlighted one gives `build_daily_orders` its datasets: it reads `dev.raw_orders` and writes `dev.daily_orders`. The tasks reach PostgreSQL through an Airflow connection, a stored address and login that a task names with `conn_id`. This adds the connection `odctl_postgres`, with the user and password of odctl's PostgreSQL:

```bash title="docs/snippets/lineage/commands.sh:airflow-connection"
docker exec airflow airflow connections add odctl_postgres \
  --conn-type postgres --conn-host postgres --conn-login user --conn-password password \
  --conn-schema odctl --conn-port 5432
```

The command prints ``Successfully added `conn_id`=odctl_postgres`` and a table with the connection. Copy the DAG into the Airflow container and upload it to `s3://airflow/dags`, as [Airflow DAGs from S3](airflow-dags.md#upload-a-dag) does:

```bash title="docs/snippets/lineage/commands.sh:airflow-upload"
docker cp lineage_orders.py airflow:/tmp/lineage_orders.py
docker exec airflow python -c '
import boto3
boto3.client("s3", endpoint_url="http://seaweed:8333").upload_file(
    "/tmp/lineage_orders.py", "airflow", "dags/lineage_orders.py")'
```

Airflow reads the bucket every 15 seconds, so the DAG appears in its list a short time after the upload. Wait until the first command lists it, then unpause the DAG and trigger a run:

```bash title="docs/snippets/lineage/commands.sh:airflow-run"
docker exec airflow airflow dags list | grep lineage_orders
docker exec airflow airflow dags unpause lineage_orders
docker exec airflow airflow dags trigger lineage_orders
```

The last command prints the new run in state `queued`. Airflow sends the events while the run executes, and the run takes a few seconds, so list the runs until the state is `success` with `docker exec airflow airflow dags list-runs lineage_orders`. Then read the jobs back. A namespace groups jobs and datasets in Marquez. This lists the jobs of one namespace from the same API that [Read the Lineage Back](#read-the-lineage-back) uses, cut to each job's name and the datasets it read and wrote:

```bash title="docs/snippets/lineage/commands.sh:airflow-read"
# The jobs of the namespace default, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/default/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
```

```text
lineage_orders.build_daily_orders ['odctl.dev.raw_orders'] ['odctl.dev.daily_orders']
lineage_orders.seed_raw_orders [] ['odctl.dev.raw_orders']
```

Airflow's provider names each job after the DAG and the task, and each dataset after the database, the schema and the table. Three more facts explain the output:

- Airflow puts its jobs in the namespace `default`. To change it, set `AIRFLOW__OPENLINEAGE__NAMESPACE` in `.odctl/compose-orch.yml` and run `odctl recreate airflow`. Airflow gives each table the namespace `postgres://postgres:5432`, the address of the database.
- The DAG is a third job, `lineage_orders`, with no datasets, so the read-back leaves it out.
- The first task writes `raw_orders` and the second reads it, so the graph joins the two jobs through that table.

The UI draws the graph of the second task at [http://127.0.0.1:3003/lineage/job/default/lineage_orders.build_daily_orders](http://127.0.0.1:3003/lineage/job/default/lineage_orders.build_daily_orders):

![Marquez lineage graph of the two Airflow tasks, joined by the table raw_orders](../images/marquez-airflow.png){ .screenshot }

The graph runs from `seed_raw_orders` through the table `raw_orders` to `build_daily_orders` and `daily_orders`, because the second task reads the table the first one wrote.

## Lineage from Spark

The OpenLineage Spark listener is a Spark listener, a class that Spark calls as a job runs. It sends the events with the datasets each statement read and wrote. Its jar, `openlineage.jar`, is in `/mnt/shared-deps/spark`, which the Spark containers already put on the classpath, so the job needs no `--packages` option. This section builds on [Spark](spark.md). Start the profile:

```bash title="docs/snippets/lineage/commands.sh:spark-up"
odctl up spark-lite
```

`spark-full` works the same way, because it runs the same `spark-master` container.

Save this PySpark job as `orders_job.py`. It writes the Iceberg table `raw_orders` and then builds `daily_orders` from it:

```python title="docs/snippets/lineage/orders_job.py" hl_lines="14-16"
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("spark-orders").getOrCreate()

spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.demo")
spark.sql("""
  CREATE OR REPLACE TABLE iceberg.demo.raw_orders (supplier STRING, price DOUBLE)
  USING iceberg""")
spark.sql("""
  INSERT INTO iceberg.demo.raw_orders VALUES ('a', 5.0), ('a', 10.0), ('b', 7.5)""")
spark.sql("""
  CREATE OR REPLACE TABLE iceberg.demo.daily_orders (supplier STRING, total DOUBLE)
  USING iceberg""")
spark.sql("""
  INSERT INTO iceberg.demo.daily_orders
  SELECT supplier, sum(price) FROM iceberg.demo.raw_orders GROUP BY supplier""")
```

The job has no lineage code. The listener reads each statement's plan, and the highlighted statement is the one that reads `raw_orders` and writes `daily_orders`. Copy the file into the master container and submit it with the listener's settings:

```bash title="docs/snippets/lineage/commands.sh:spark-submit" hl_lines="4-8"
docker cp orders_job.py spark-master:/tmp/orders_job.py
# Submit the job with the OpenLineage listener sending to marquez-api.
docker exec spark-master /opt/spark/bin/spark-submit \
  --driver-class-path '/mnt/shared-deps/spark/openlineage.jar:/mnt/shared-deps/shared/*:/mnt/shared-deps/spark/*' \
  --conf spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener \
  --conf spark.openlineage.transport.type=http \
  --conf spark.openlineage.transport.url=http://marquez-api:5000 \
  --conf spark.openlineage.namespace=odctl \
  /tmp/orders_job.py
```

Each setting does one thing:

- `--driver-class-path` puts `openlineage.jar` first on the driver's classpath, ahead of the other jars of the shared volume. The OpenMetadata agent jar in that folder holds a second copy of the listener's classes, and with Spark's default classpath the driver loads that copy: the listener fails with `NoSuchMethodError`, Spark stops the session, and the job fails. The value repeats the classpath from `spark/spark-defaults.conf` in the workspace, with the jar in front.
- `spark.extraListeners` names the listener class, so Spark calls it for every statement.
- `spark.openlineage.transport.type` and `spark.openlineage.transport.url` send the events over HTTP to `marquez-api`.
- `spark.openlineage.namespace` is the namespace of the jobs in Marquez.

The job prints Spark's usual log, with some OpenLineage warnings and one `ContextFactory` error line, and the events still reach Marquez. Spark sends them as each statement ends, so read the jobs of the namespace `odctl` back a few seconds after the job ends:

```bash title="docs/snippets/lineage/commands.sh:spark-read"
# The jobs of the namespace odctl, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/odctl/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
```

```text
spark_orders.append_data.iceberg_demo_daily_orders ['demo/raw_orders'] ['demo/daily_orders']
spark_orders.atomic_replace_table.demo_daily_orders [] ['demo/daily_orders']
spark_orders.append_data.iceberg_demo_raw_orders [] ['demo/raw_orders']
spark_orders.atomic_replace_table.demo_raw_orders [] ['demo/raw_orders']
```

Spark reports one job for each statement that writes a table. The listener names each job after the application name, with `-` turned into `_` (`spark_orders`), the kind of write and the table. The first line is the job that read `raw_orders` and wrote `daily_orders`. The listener names an Iceberg table by its place in the warehouse bucket, so the datasets are `demo/raw_orders` and `demo/daily_orders` in the namespace `s3://warehouse`. The application is a fifth job, `spark_orders`, with no datasets, so the read-back leaves it out.

## Lineage from Feast

`feast apply` can send an event for the feature views it applies. It does so when the `openlineage` block of `feature_store.yaml` says `enabled: true`. The bundled repository of the `feast` profile has no such block, so Feast sends nothing until you add one.

The block needs the OpenLineage extra of the Feast client. The `airflow` image has it and the `feast` services do not, so this section runs `feast apply` in the `airflow` container, started in [Lineage from Airflow](#lineage-from-airflow). It builds on [Feast with Iceberg](feast-iceberg.md), whose `feature_repo/definitions.py` it uses: save that file first if you have not. The feature view `driver_stats` is over the Iceberg table `demo.driver_stats`, and `apply` does not read the table.

Save this file as `lineage_repo/feature_store.yaml`. It differs from the Feast guide's file in three places: the project, `lineage_demo`, which keeps these feature views apart from the guide's project `demo`; the addresses, which are the container addresses because `feast apply` runs inside the `odctl` network; and the `openlineage` block:

```yaml title="docs/snippets/lineage/lineage_repo/feature_store.yaml" hl_lines="12-15"
project: lineage_demo
provider: local
registry:
  registry_type: sql
  path: postgresql+psycopg://user:password@postgres:5432/feast
offline_store:
  type: duckdb
online_store:
  type: redis
  connection_string: "valkey:6379,username=user,password=password"
entity_key_serialization_version: 3
openlineage:
  enabled: true
  transport_type: http
  transport_url: http://marquez-api:5000
```

`transport_type` and `transport_url` send the events over HTTP to `marquez-api`, and Feast adds the path `api/v1/lineage` itself. Without `namespace`, Feast uses the project name as the namespace. Run these from the folder that holds `feature_repo` and `lineage_repo`. Copy both files into the container and apply them. `--skip-source-validation` is the option that [Feast with Iceberg](feast-iceberg.md#register-and-materialise) explains:

```bash title="docs/snippets/lineage/commands.sh:feast-apply"
docker exec airflow mkdir -p /tmp/lineage_repo
docker cp lineage_repo/feature_store.yaml airflow:/tmp/lineage_repo/feature_store.yaml
docker cp feature_repo/definitions.py airflow:/tmp/lineage_repo/definitions.py
docker exec airflow feast -c /tmp/lineage_repo apply --skip-source-validation
```

```text
INFO:openlineage.client.client:OpenLineageClient will use `http` transport
No project found in the repository. Using project name lineage_demo defined in feature_store.yaml
Applying changes for project lineage_demo
Deploying infrastructure for driver_stats
```

The first line shows that the OpenLineage client is on. Read the jobs of the namespace `lineage_demo`, the project name, back:

```bash title="docs/snippets/lineage/commands.sh:feast-read"
# The jobs of the namespace lineage_demo, the name of the Feast project, with the datasets each read and wrote.
curl -s http://127.0.0.1:5002/api/v1/namespaces/lineage_demo/jobs | python3 -c '
import json, sys
for job in json.load(sys.stdin)["jobs"]:
    if job["inputs"] or job["outputs"]:
        print(job["name"], [d["name"] for d in job["inputs"]], [d["name"] for d in job["outputs"]])'
```

```text
feast_feature_views_lineage_demo ['driver', '.demo.driver_stats'] ['driver_stats']
```

Feast reports one job for the project's feature views. Its inputs are the entity `driver` and the data source, and its output is the feature view `driver_stats`. The source is named `.demo.driver_stats` because an `IcebergSource` with no `name` joins its `warehouse`, `namespace` and `table`, and the definitions pass an empty `warehouse`.

## From Another Container

Inside the [`odctl` network](../how-it-works.md#how-you-reach-a-service), send events to `http://marquez-api:5000/api/v1/lineage`. For an OpenLineage client's HTTP transport, set the URL to `http://marquez-api:5000`, because the transport adds `api/v1/lineage` by default.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It gives each run a new id, so it reports a new run every time:

```bash title="docs/snippets/lineage/example.sh"
#!/usr/bin/env bash
# Starts lineage, reports one run of a job that reads raw-orders and writes
# demo-dataset, and prints the state of the job's latest run.
set -euo pipefail

odctl up lineage

RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
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

curl -s http://127.0.0.1:5002/api/v1/namespaces/demo/jobs/demo-job \
  | python3 -c 'import json, sys; run = json.load(sys.stdin)["latestRun"]; print(run["id"], run["state"])'
```

It prints the new run's id and `COMPLETED`.
