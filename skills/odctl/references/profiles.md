# odctl Profiles

Each section gives a profile's addresses from the host and from a container, its logins, what `odctl up` also starts, its services with their images, ports and memory limits, which services `odctl up` waits for, and where its data lives. Every port is published on `127.0.0.1` only. This page is generated from odctl's `registry.yml` and compose files.

## Contents

- Messaging: [kafka-lite](#kafka-lite), [kafka-full](#kafka-full)
- Stream and Batch Processing: [flink-lite](#flink-lite), [flink-full](#flink-full), [spark-lite](#spark-lite), [spark-full](#spark-full)
- Analytics: [ch-lite](#ch-lite), [ch-full](#ch-full), [trino](#trino), [metabase](#metabase)
- Orchestration: [airflow](#airflow), [temporal](#temporal)
- MLOps: [mlflow](#mlflow), [feast](#feast), [evidently](#evidently), [label-studio](#label-studio)
- Metadata and Lineage: [metadata](#metadata), [lineage](#lineage)
- Observability: [telemetry](#telemetry)
- Storage and Catalog: [postgres](#postgres), [storage](#storage), [catalog](#catalog), [valkey](#valkey), [fluss](#fluss), [deps](#deps)
- AI Engineering: [langfuse](#langfuse)

## Messaging

### kafka-lite

Kafka: Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers. `odctl up kafka-lite` also starts: `deps`.

```text
• Kafka UI:
  - External (host): http://127.0.0.1:8086
  - Internal (Docker): http://kafka-ui:8080
• Schema Registry & Connect:
  - External (host): http://127.0.0.1:8081 / http://127.0.0.1:8083
• Bootstrap Servers (1-Node Lite):
  - External (host): 127.0.0.1:9092
  - Internal (Docker): broker-1:19092
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `kafka` | `apache/kafka` | `9092:9092` | `1500m` |
| `connect` | `apache/kafka` | `8083:8083` | `2g` |
| `karapace` | `ghcr.io/aiven-open/karapace` | `8081:8081` | `512m` |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui` | `8086:8080` | `512m` |

Health: `kafka`, `connect`, `karapace` and `kafka-ui` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

### kafka-full

Kafka: Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers. `odctl up kafka-full` also starts: `deps`.

```text
• Kafka UI:
  - External (host): http://127.0.0.1:8086
  - Internal (Docker): http://kafka-ui:8080
• Schema Registry & Connect:
  - External (host): http://127.0.0.1:8081 / http://127.0.0.1:8083
• Bootstrap Servers (3-Node Cluster):
  - External (host): 127.0.0.1:9092, 127.0.0.1:9093, 127.0.0.1:9094
  - Internal (Docker): broker-1:19092, broker-2:19093, broker-3:19094
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `kafka-1` | `apache/kafka` | `9092:9092` | `1500m` |
| `kafka-2` | `apache/kafka` | `9093:9093` | `1500m` |
| `kafka-3` | `apache/kafka` | `9094:9094` | `1500m` |
| `connect` | `apache/kafka` | `8083:8083` | `2g` |
| `karapace` | `ghcr.io/aiven-open/karapace` | `8081:8081` | `512m` |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui` | `8086:8080` | `512m` |

Health: `kafka-1`, `kafka-2`, `kafka-3`, `connect`, `karapace` and `kafka-ui` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

## Stream and Batch Processing

### flink-lite

Apache Flink: Stateful, real-time stream processing engine. Lite uses 1 TaskManager; Full uses 3 TaskManagers. `odctl up flink-lite` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Flink JobManager UI (1 TaskManager):
  - External (host): http://127.0.0.1:8082
  - Internal (Docker): http://jobmanager:8081
• SQL Gateway REST:
  - External (host): http://127.0.0.1:8084
  - Internal (Docker): http://flink-sql-gateway:8083
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `jobmanager` | `flink` | `8082:8081` | `1500m` |
| `taskmanager-a` | `flink` | none | `3500m` |
| `sql-gateway` | `flink` | `8084:8083` | `1g` |

Health: `odctl up` and `odctl recreate` return once `jobmanager` (`curl -f http://localhost:8081/config`) passes its health check, so call what the check tests with no wait loop. `taskmanager-a` and `sql-gateway` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

### flink-full

Apache Flink: Stateful, real-time stream processing engine. Lite uses 1 TaskManager; Full uses 3 TaskManagers. `odctl up flink-full` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Flink JobManager UI (3 TaskManagers):
  - External (host): http://127.0.0.1:8082
  - Internal (Docker): http://jobmanager:8081
• SQL Gateway REST:
  - External (host): http://127.0.0.1:8084
  - Internal (Docker): http://flink-sql-gateway:8083
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `jobmanager` | `flink` | `8082:8081` | `1500m` |
| `taskmanager-a` | `flink` | none | `3500m` |
| `taskmanager-b` | `flink` | none | `3500m` |
| `taskmanager-c` | `flink` | none | `3500m` |
| `sql-gateway` | `flink` | `8084:8083` | `1g` |

Health: `odctl up` and `odctl recreate` return once `jobmanager` (`curl -f http://localhost:8081/config`) passes its health check, so call what the check tests with no wait loop. `taskmanager-a`, `taskmanager-b`, `taskmanager-c` and `sql-gateway` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

### spark-lite

Apache Spark: Distributed batch and micro-batch data processing. Lite uses 1 Worker; Full uses 3 Workers. `odctl up spark-lite` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Spark Master UI (1 Worker):
  - External (host): http://127.0.0.1:9080
  - Internal (Docker): http://spark-master:8080
• Master RPC:
  - External (host): spark://127.0.0.1:7077
  - Internal (Docker): spark://spark-master:7077
• Spark History Server:
  - External (host): http://127.0.0.1:18080
  - Internal (Docker): http://spark-history:18080
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `spark-master` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9080:8080`, `7077:7077` | `1g` |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9081:8081` | `2g` |
| `spark-history` | `ghcr.io/jaehyeon-kim/odctl/spark` | `18080:18080` | `1g` |

Health: `odctl up` and `odctl recreate` return once `spark-master` (`curl -f http://localhost:8080`) passes its health check, so call what the check tests with no wait loop. `spark-worker-1` and `spark-history` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it. The named volume `spark-events-data` holds Spark's event logs in memory, so it holds nothing once the stack is down.

### spark-full

Apache Spark: Distributed batch and micro-batch data processing. Lite uses 1 Worker; Full uses 3 Workers. `odctl up spark-full` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Spark Master UI (3 Workers):
  - External (host): http://127.0.0.1:9080
  - Internal (Docker): http://spark-master:8080
• Master RPC:
  - External (host): spark://127.0.0.1:7077
  - Internal (Docker): spark://spark-master:7077
• Spark History Server:
  - External (host): http://127.0.0.1:18080
  - Internal (Docker): http://spark-history:18080
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `spark-master` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9080:8080`, `7077:7077` | `1g` |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9081:8081` | `2g` |
| `spark-worker-2` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9082:8081` | `2g` |
| `spark-worker-3` | `ghcr.io/jaehyeon-kim/odctl/spark` | `9083:8081` | `2g` |
| `spark-history` | `ghcr.io/jaehyeon-kim/odctl/spark` | `18080:18080` | `1g` |

Health: `odctl up` and `odctl recreate` return once `spark-master` (`curl -f http://localhost:8080`) passes its health check, so call what the check tests with no wait loop. `spark-worker-1`, `spark-worker-2`, `spark-worker-3` and `spark-history` have no health check: the commands return once they run, so wait for what the task needs from them, with a limit.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it. The named volume `spark-events-data` holds Spark's event logs in memory, so it holds nothing once the stack is down.

## Analytics

### ch-lite

ClickHouse: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up ch-lite` also starts: `deps`.

```text
• ClickHouse HTTP (Shard 1 / Replica 1 & 2):
  * External (host): http://127.0.0.1:8123, http://127.0.0.1:8124
  * Internal (Docker): http://ch-11:8123, http://ch-12:8123
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `ch-keeper` | `clickhouse/clickhouse-keeper` | `9181:9181` | `512m` |
| `ch-shard2-stub` | `alpine` | none | `64m` |
| `ch-11` | `clickhouse/clickhouse-server` | `8123:8123`, `9000:9000` | `4g` |
| `ch-12` | `clickhouse/clickhouse-server` | `8124:8123`, `9001:9000` | `4g` |

Health: `odctl up` and `odctl recreate` return once `ch-keeper` (`echo ruok | nc 127.0.0.1 9181`), `ch-11` (`clickhouse-client --password password --query SELECT 1`) and `ch-12` (`clickhouse-client --password password --query SELECT 1`) pass their health checks, so call what the check tests with no wait loop. `ch-shard2-stub` has no health check: the commands return once it runs, so wait for what the task needs from it, with a limit.

Login: the user `default` with the password `password`, from the host and from a container (`CLICKHOUSE_PASSWORD` in `compose-analytics.yml`). A request with no password fails with `AUTHENTICATION_FAILED`.

Data: `ch-keeper`, `ch-11` and `ch-12` keep their data in unnamed volumes that their images declare: `odctl recreate` keeps it, and `odctl down` loses it. The other services keep their data inside their containers.

### ch-full

ClickHouse: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up ch-full` also starts: `deps`.

```text
• ClickHouse HTTP (Shards 1 & 2 / Replicas 1 & 2):
  * External (host): http://127.0.0.1:8123, http://127.0.0.1:8124, http://127.0.0.1:8125, http://127.0.0.1:8126
  * Internal (Docker): http://ch-11:8123, http://ch-12:8123, http://ch-21:8123, http://ch-22:8123
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `ch-keeper` | `clickhouse/clickhouse-keeper` | `9181:9181` | `512m` |
| `ch-11-full` | `clickhouse/clickhouse-server` | `8123:8123`, `9000:9000` | `4g` |
| `ch-12-full` | `clickhouse/clickhouse-server` | `8124:8123`, `9001:9000` | `4g` |
| `ch-21` | `clickhouse/clickhouse-server` | `8125:8123`, `9002:9000` | `4g` |
| `ch-22` | `clickhouse/clickhouse-server` | `8126:8123`, `9003:9000` | `4g` |

Health: `odctl up` and `odctl recreate` return once `ch-keeper` (`echo ruok | nc 127.0.0.1 9181`), `ch-11-full` (`clickhouse-client --password password --query SELECT 1`), `ch-12-full` (`clickhouse-client --password password --query SELECT 1`), `ch-21` (`clickhouse-client --password password --query SELECT 1`) and `ch-22` (`clickhouse-client --password password --query SELECT 1`) pass their health checks, so call what the check tests with no wait loop.

Login: the user `default` with the password `password`, from the host and from a container (`CLICKHOUSE_PASSWORD` in `compose-analytics.yml`). A request with no password fails with `AUTHENTICATION_FAILED`.

Data: `ch-keeper`, `ch-11-full`, `ch-12-full`, `ch-21` and `ch-22` keep their data in unnamed volumes that their images declare: `odctl recreate` keeps it, and `odctl down` loses it.

### trino

Trino: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up trino` also starts: `deps`, `postgres`.

```text
• Trino UI & JDBC connection (no password: no authenticator is
  configured, so any username is accepted):
  * External (host): http://127.0.0.1:8080
  * Internal (Docker): http://trino:8080
• Identities: `docker exec trino trino --execute '<query>'` runs the
  query as `trino`, the CLI default. Pass `--user user` for the
  stack-wide convention, or `--user analyst`, which trino/rules.json
  denies schema ownership while leaving every table privilege in place.
• Catalogs: postgres works with the trino profile alone. iceberg,
  kafka, clickhouse and valkey load without their backing services,
  so they appear in SHOW CATALOGS and then fail at query time unless
  catalog, storage, kafka-lite, ch-lite or valkey is also up.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `trino` | `trinodb/trino` | `8080:8080` | `4g` |

Health: `odctl up` and `odctl recreate` return once `trino` (`curl -f http://localhost:8080/v1/info`) passes its health check, so call what the check tests with no wait loop.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

### metabase

Metabase: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up metabase` also starts: `deps`, `postgres`.

```text
• Metabase Dashboard Engine:
  * External (host): http://127.0.0.1:3000
  * Internal (Docker): http://metabase:3000
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `metabase` | `metabase/metabase` | `3000:3000` | `1500m` |

Health: `odctl up` and `odctl recreate` return once `metabase` (`curl -f http://localhost:3000/api/health`) passes its health check, so call what the check tests with no wait loop.

Data: `metabase` keeps its data in the `metabase` database of the `postgres` profile, so `odctl down metabase` and `odctl recreate metabase` keep it while `postgres` runs, and `odctl down postgres` loses it.

## Orchestration

### airflow

Apache Airflow: Workflow orchestration and pipeline scheduling (Airflow), and durable workflows written in code (Temporal). `odctl up airflow` also starts: `deps`, `postgres`, `storage`.

```text
• Airflow Web UI (Credentials: user / password):
  * External (host): http://127.0.0.1:8085
  * Internal (Docker): http://airflow:8080
• DAGs: read from s3://airflow/dags every 15 seconds.
• Plugins: copied from s3://airflow/plugins at start. Airflow loads
  plugins only once, so run `odctl restart airflow` after changing one.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `airflow` | `ghcr.io/jaehyeon-kim/odctl/airflow` | `8085:8080` | `3g` |

Health: `odctl up` and `odctl recreate` return once `airflow` (`curl -fs http://localhost:8080/api/v2/monitor/health`) passes its health check, so call what the check tests with no wait loop.

DAGs: a new DAG starts paused (`AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION` in `compose-orch.yml`), and a run triggered on a paused DAG stays queued. After an upload, wait with a limit until Airflow lists the DAG, then unpause it (`airflow dags unpause <dag_id>`, or `PATCH /api/v2/dags/<dag_id>` with `{"is_paused": false}`) and trigger it. Unpausing a DAG that has a schedule also starts a scheduled run. On a stack where the DAG was uploaded before, Airflow lists the stored DAG before it parses the new file.

Data: `airflow` keeps its data in the `airflow` database of the `postgres` profile, so `odctl down airflow` and `odctl recreate airflow` keep it while `postgres` runs, and `odctl down postgres` loses it.

### temporal

Temporal: Workflow orchestration and pipeline scheduling (Airflow), and durable workflows written in code (Temporal). `odctl up temporal` also starts: `deps`.

```text
• Temporal Web UI:
  * External (host): http://127.0.0.1:8233
  * Internal (Docker): http://temporal:8233
• gRPC endpoint for SDK clients and workers (namespace "default"):
  * External (host): 127.0.0.1:7233
  * Internal (Docker): temporal:7233
• Your environment needs: temporalio. odctl runs only the server, so
  your own process runs the worker that executes workflows and
  activities.
• Development server: the server, the UI and a SQLite database in one
  process. History survives `odctl restart` and is lost on
  `odctl down`, like every odctl service's data.
• Prometheus metrics: http://temporal:9090/metrics, inside the network.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `temporal` | `temporalio/temporal` | `7233:7233`, `8233:8233` | `1g` |

Health: `odctl up` and `odctl recreate` return once `temporal` (`temporal operator cluster health --address 127.0.0.1:7233`) passes its health check, so call what the check tests with no wait loop.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

## MLOps

### mlflow

MLflow: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), ML monitoring (Evidently), and data labelling (Label Studio). `odctl up mlflow` also starts: `deps`, `postgres`, `storage`.

```text
• MLflow Tracking UI & Artifact Registry Server:
  * External (host): http://127.0.0.1:5004
  * Internal (Docker): http://mlflow:5000
• MLflow Model Scoring Server, idle until MODEL_URI in .env names a model;
  run `odctl up mlflow` again after setting it. It loads the model once,
  when it starts, so a new version behind the same alias needs
  `odctl restart mlflow`, and the server answers nothing for about 16 seconds:
  * External (host): http://127.0.0.1:5003/invocations
  * Internal (Docker): http://mlflow-serve:5003/invocations
• Liveness: http://127.0.0.1:5003/ping and http://127.0.0.1:5003/health
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `mlflow` | `ghcr.io/jaehyeon-kim/odctl/mlflow` | `5004:5000` | `2500m` |
| `mlflow-serve` | `ghcr.io/jaehyeon-kim/odctl/mlflow` | `5003:5003` | `1500m` |

Health: `odctl up` and `odctl recreate` return once `mlflow` (`curl -f http://localhost:5000/health`) and `mlflow-serve` (`[ -z "${MODEL_URI}" ] || curl -f http://localhost:5003/ping`) pass their health checks, so call what the check tests with no wait loop.

Data: `mlflow` keeps its data in the `mlflow` database of the `postgres` profile, so `odctl down mlflow` and `odctl recreate mlflow` keep it while `postgres` runs, and `odctl down postgres` loses it. The other services keep their data inside their containers.

### feast

Feast: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), ML monitoring (Evidently), and data labelling (Label Studio). `odctl up feast` also starts: `catalog`, `deps`, `postgres`, `storage`, `valkey`.

```text
• Feast UI (registry browser, not data):
  * External (host): http://127.0.0.1:8890
  * Internal (Docker): http://feast-ui:8888
• Upload your feature repository to s3://feast/repo. The services check
  it every 15 seconds and restart Feast when it changes. Run
  `feast apply` from your own environment. odctl ships no definitions.
• Your environment needs: feast[duckdb,iceberg,redis,postgres]
• On an IcebergSource against catalog, pass warehouse="" and
  catalog_name="odctl". The REST client puts warehouse in the URL path,
  and Iceberg's REST fixture server serves the spec with no prefix.
• Online feature server for get_online_features:
  * External (host): http://127.0.0.1:6566
  * Internal (Docker): http://feast-serve:6566
• MCP endpoint, for agents that list Feast's tools and read features:
  http://127.0.0.1:6566/mcp
• Liveness: http://127.0.0.1:6566/health
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `feast-ui` | `quay.io/feastdev/feature-server` | `8890:8888` | `1g` |
| `feast-serve` | `quay.io/feastdev/feature-server` | `6566:6566` | `1g` |

Health: `odctl up` and `odctl recreate` return once `feast-ui` (`curl -f http://localhost:8888/api/v1/projects`) and `feast-serve` (`curl -f http://localhost:6566/health`) pass their health checks, so call what the check tests with no wait loop.

Registry:the bundled `feature_store.yaml` keeps Feast's SQL registry in the `feast` database of `postgres`: `postgresql+psycopg://user:password@postgres:5432/feast` from a container, and `127.0.0.1:5432` from the host. The online store is `valkey`.

Data: `feast-ui` and `feast-serve` keep their data in the `feast` database of the `postgres` profile, so `odctl down feast` and `odctl recreate feast` keep it while `postgres` runs, and `odctl down postgres` loses it.

### evidently

Evidently: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), ML monitoring (Evidently), and data labelling (Label Studio). `odctl up evidently` also starts: `deps`, `postgres`.

```text
• Evidently UI & API (no login, and writes are open):
  * External (host): http://127.0.0.1:8089
  * Internal (Docker): http://evidently:8000
• Push reports with RemoteWorkspace("http://127.0.0.1:8089") from the
  host, or RemoteWorkspace("http://evidently:8000") from a container.
  Reports are computed by the client, so it needs evidently==0.7.23 and pandas<3.1.
  In Airflow, set _AIRFLOW_PIP_DEPS="evidently==0.7.23" in .env.
• Projects, reports, dashboards and datasets: the evidently database
  on Postgres.
• Settings: evidently/config.yaml in the workspace.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `evidently` | `evidently/evidently-service` | `8089:8000` | `1g` |

Health: `odctl up` and `odctl recreate` return once `evidently` (`python -c import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v2/projects', timeout=5)`) passes its health check, so call what the check tests with no wait loop.

Data: `evidently` keeps its data in the `evidently` database of the `postgres` profile, so `odctl down evidently` and `odctl recreate evidently` keep it while `postgres` runs, and `odctl down postgres` loses it.

### label-studio

Label Studio: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), ML monitoring (Evidently), and data labelling (Label Studio). `odctl up label-studio` also starts: `deps`, `postgres`.

```text
• Label Studio UI & API (user user@odctl.io, password password):
  * External (host): http://127.0.0.1:8088
  * Internal (Docker): http://label-studio:8080
• API token: odctl-label-studio-token, sent as the header
  Authorization: Token odctl-label-studio-token
• Projects, tasks and annotations: the labelstudio database on Postgres.
• S3 storage: the label-studio bucket on SeaweedFS (start storage),
  with the endpoint field left empty and pre-signed URLs off.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `label-studio` | `heartexlabs/label-studio` | `8088:8080` | `768m` |

Health: `odctl up` and `odctl recreate` return once `label-studio` (`curl -f http://localhost:8080/health/`) passes its health check, so call what the check tests with no wait loop.

Data: `label-studio` keeps its data in the `labelstudio` database of the `postgres` profile, so `odctl down label-studio` and `odctl recreate label-studio` keep it while `postgres` runs, and `odctl down postgres` loses it.

## Metadata and Lineage

### metadata

OpenMetadata: Data catalog, discovery, and governance platform. `odctl up metadata` also starts: `deps`, `postgres`, `storage`.

```text
• OpenMetadata UI & REST API (Credentials: admin@odctl.io / password,
  or user@odctl.io / password, on a new database; a database from
  1.3.0 to 1.6.0 keeps admin@odctl.io / admin, and one from an earlier
  release keeps admin@open-data.local and user@open-data.local, both
  with the password admin):
  - External (host): http://127.0.0.1:8585
  - Internal (Docker): http://openmetadata-server:8585
• Ingestion Pipeline UI (Credentials: user / password):
  - External (host): http://127.0.0.1:8087
  - Internal (Docker): http://openmetadata-ingestion:8080
• Custom connectors: files in s3://openmetadata/connectors, checked every
  15 seconds and copied into the ingestion container when they change.
• AutoPilot (default agents for a service added in the UI) is off unless
  METADATA_AUTOPILOT="true" is set in .odctl/.env.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `openmetadata-es` | `docker.elastic.co/elasticsearch/elasticsearch` | `9200:9200`, `9300:9300` | `2g` |
| `openmetadata-migrate` | `docker.getcollate.io/openmetadata/server` | none | `1g` |
| `openmetadata-server` | `docker.getcollate.io/openmetadata/server` | `8585:8585`, `8586:8586` | `2g` |
| `openmetadata-ingestion` | `docker.getcollate.io/openmetadata/ingestion` | `8087:8080` | `1500m` |
| `openmetadata-init` | `docker.getcollate.io/openmetadata/ingestion` | none | `64m` |

Health: `odctl up` and `odctl recreate` return once `openmetadata-es` (`curl -s http://localhost:9200/_cluster/health?pretty | grep status | grep -qE 'green|yellow'`), `openmetadata-server` (`wget -q --spider http://localhost:8586/healthcheck`) and `openmetadata-ingestion` (`curl -fs http://localhost:8080/pluginsv2/api/v2/openmetadata/health`) pass their health checks, so call what the check tests with no wait loop.

Agents: after `POST /api/v1/services/ingestionPipelines/deploy/<id>`, the ingestion Airflow parses the new DAG before `POST .../trigger/<id>` works, so repeat the trigger every 5 seconds, with a limit, until it answers that the workflow has been triggered.

Data: `openmetadata-migrate`, `openmetadata-server` and `openmetadata-ingestion` keep their data in the `omt` database of the `postgres` profile, so `odctl down metadata` and `odctl recreate metadata` keep it while `postgres` runs, and `odctl down postgres` loses it. The other services keep their data inside their containers.

### lineage

Marquez: System telemetry, monitoring, and data lineage. `odctl up lineage` also starts: `deps`, `postgres`.

```text
• Marquez API Metadata Endpoint:
  * External (host): http://127.0.0.1:5002
  * Internal (Docker): http://marquez-api:5000
• Marquez Lineage Graph Web UI:
  * External (host): http://127.0.0.1:3003
  * Internal (Docker): http://marquez-web:3000
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `marquez-api` | `marquezproject/marquez` | `5002:5000`, `5001:5001` | `1g` |
| `marquez-web` | `marquezproject/marquez-web` | `3003:3000` | `512m` |

Health: `odctl up` and `odctl recreate` return once `marquez-api` (`curl -fsS http://localhost:5001/healthcheck`) passes its health check, so call what the check tests with no wait loop. `marquez-web` has no health check: the commands return once it runs, so wait for what the task needs from it, with a limit.

Data: `marquez-api` keeps its data in the `marquez` database of the `postgres` profile, so `odctl down lineage` and `odctl recreate lineage` keep it while `postgres` runs, and `odctl down postgres` loses it. The other services keep their data inside their containers.

## Observability

### telemetry

Telemetry (grafana/otel-lgtm): System telemetry, monitoring, and data lineage. `odctl up telemetry` also starts: `deps`.

```text
• Prometheus Time Series Engine (also takes OTLP at /api/v1/otlp/v1/metrics):
  * External (host): http://127.0.0.1:19090
  * Internal (Docker): http://prometheus:9090
• Grafana Dashboards (Credentials: user / password):
  * External (host): http://127.0.0.1:3004
  * Internal (Docker): http://grafana:3000
  * A dashboard per service in the odctl folder, which fills in once
    that service's profile is up.
  * Alert rules from .odctl/grafana/alerting, loaded when telemetry
    starts: one fires after a failed Airflow DAG run. No contact point
    is configured, so a firing rule shows only on the Alerting page.
• OTLP Receiver (metrics, traces and logs):
  * External (host): 127.0.0.1:4317 (gRPC), http://127.0.0.1:4318 (HTTP)
  * Internal (Docker): otel-lgtm:4317 (gRPC), http://otel-lgtm:4318 (HTTP)
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `otel-lgtm` | `grafana/otel-lgtm` | `19090:9090`, `3004:3000`, `4317:4317`, `4318:4318` | `2g` |

Health: `odctl up` and `odctl recreate` return once `otel-lgtm` (`test -f /tmp/ready && curl -fsS http://localhost:9090/-/ready`) passes its health check, so call what the check tests with no wait loop.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

## Storage and Catalog

### postgres

PostgreSQL: PostgreSQL metadata backend. `odctl up postgres` also starts: `deps`.

```text
• Postgres JDBC:
  - External (host): jdbc:postgresql://127.0.0.1:5432/odctl
  - Internal (Docker): jdbc:postgresql://postgres:5432/odctl
  - Credentials: user / password
• Extensions, created in the `vector` database:
  - vector (pgvector): vector columns and HNSW or IVFFlat indexes
  - pg_textsearch: BM25 keyword ranking, for hybrid search with pgvector
  - postgis: geometry and geography types and spatial queries
  Run CREATE EXTENSION in another database to use them there.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `postgres` | `ghcr.io/jaehyeon-kim/odctl/postgres` | `5432:5432` | `1g` |

Health: `odctl up` and `odctl recreate` return once `postgres` (`pg_isready -U ${POSTGRES_USER:-user} -d metabase`) passes its health check, so call what the check tests with no wait loop.

Data: `postgres` keeps its data in unnamed volumes that its image declares: `odctl recreate` keeps it, and `odctl down` loses it. `TZ` and `postgres/01-init-databases.sh`, which creates each service's database, take effect only when PostgreSQL creates its data folder. A recreate keeps that folder, so they change after `odctl down postgres` and `odctl up postgres`.

### storage

SeaweedFS: SeaweedFS S3-compatible object storage. `odctl up storage` also starts: `deps`.

```text
• S3 Browser UI:
  - External (host): http://127.0.0.1:8889
  - Internal (Docker): http://seaweed:8888
• S3 API Endpoint:
  - External (host): http://127.0.0.1:8333
  - Internal (Docker): http://seaweed:8333
  - Default AWS Keys: user / password
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `seaweed` | `chrislusf/seaweedfs` | `8333:8333`, `8889:8888`, `9333:9333` | `1024m` |
| `seaweed-init` | `chrislusf/seaweedfs` | none | not set |

Health: `odctl up` and `odctl recreate` return once `seaweed` (`curl -f http://localhost:8888/`) passes its health check, so call what the check tests with no wait loop.

Data: `seaweed` keeps its data in unnamed volumes that its image declares: `odctl recreate` keeps it, and `odctl down` loses it. The other services keep their data inside their containers.

### catalog

Iceberg REST Catalog: Iceberg REST Catalog. `odctl up catalog` also starts: `deps`, `postgres`, `storage`.

```text
• REST API Endpoint:
  - External (host): http://127.0.0.1:8181
  - Internal (Docker): http://catalog:8181
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `catalog` | `azul/zulu-openjdk` | `8181:8181` | `512m` |

Health: `catalog` has no health check: the commands return once it runs, so wait for what the task needs from it, with a limit.

Data: `catalog` keeps its data in the `iceberg` database of the `postgres` profile, so `odctl down catalog` and `odctl recreate catalog` keep it while `postgres` runs, and `odctl down postgres` loses it.

### valkey

Valkey: Stream storage (Fluss) and multi-model data store (Valkey Bundle). Valkey includes advanced JSON, Bloom, and Vector Search capabilities. `odctl up valkey` also starts: `deps`.

```text
• Valkey (Multi-Model Data Store: Cache, JSON, Vector Search):
  * External (host): 127.0.0.1:6379
  * Internal (Docker): valkey:6379
  * Authentication: username 'user', password 'password'
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `valkey` | `valkey/valkey-bundle` | `6379:6379` | `512m` |

Health: `odctl up` and `odctl recreate` return once `valkey` (`VALKEYCLI_AUTH=password valkey-cli --user user ping | grep -q PONG`) passes its health check, so call what the check tests with no wait loop.

Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it.

### fluss

Apache Fluss: Stream storage (Fluss) and multi-model data store (Valkey Bundle). Valkey includes advanced JSON, Bloom, and Vector Search capabilities. `odctl up fluss` also starts: `deps`.

```text
• Fluss Coordinator API:
  * External (host): 127.0.0.1:9123
  * Internal (Docker): fluss-coordinator:9123
• The servers advertise their container names, which resolve only
  inside the odctl network, so run Fluss clients in a container, such
  as Flink.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `fluss-zookeeper` | `zookeeper` | none | `512m` |
| `fluss-coordinator` | `apache/fluss` | `9123:9123` | `1g` |
| `fluss-tablet-1` | `apache/fluss` | `9124:9123` | `2g` |

Health: `odctl up` and `odctl recreate` return once `fluss-zookeeper` (`echo ruok | nc 127.0.0.1 2181 | grep -q imok`) and `fluss-coordinator` (`timeout 3 bash -c '</dev/tcp/fluss-coordinator/9123'`) pass their health checks, so call what the check tests with no wait loop. `fluss-tablet-1` has no health check: the commands return once it runs, so wait for what the task needs from it, with a limit.

Readiness: `fluss-tablet-1` registers in ZooKeeper a few seconds after it starts, and a `CREATE TABLE` before then fails. Wait, with a limit, until `docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids` prints a list that holds `0`.

Data: `fluss-zookeeper` keeps its data in unnamed volumes that its image declares: `odctl recreate` keeps it, and `odctl down` loses it. The other services keep their data inside their containers.

### deps

Shared Dependencies: Shared dependencies, JARs, connectors, and Docker network `odctl up deps` also starts: nothing else.

```text
• Runs automatically on 'odctl up'.
• No persistent UI or ports exposed.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `init-deps` | `ghcr.io/jaehyeon-kim/odctl/deps` | none | not set |


Data: Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it. The named volume `odctl-shared-deps` holds only the jars `init-deps` copies, so `odctl down --volumes` removes it only once no other profile has a container.

## AI Engineering

### langfuse

Langfuse: Tracing and evaluation of LLM and agent applications. `odctl up langfuse` also starts: `ch-lite`, `deps`, `postgres`, `storage`, `valkey`.

```text
• Langfuse UI (Credentials: user@odctl.io / password):
  - External (host): http://127.0.0.1:3005
  - Internal (Docker): http://langfuse-web:3000
• OTLP endpoint for traces, over HTTP:
  - External (host): http://127.0.0.1:3005/api/public/otel
  - Internal (Docker): http://langfuse-web:3000/api/public/otel
• Project keys: public key pk-lf-odctl, secret key sk-lf-odctl, sent as
  HTTP Basic auth. Send the header x-langfuse-ingestion-version: 4 so
  Langfuse shows a trace at once, not up to 10 minutes later.
• Starts ch-lite, so it cannot run beside ch-full.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `langfuse-web` | `langfuse/langfuse` | `3005:3000` | `2g` |
| `langfuse-worker` | `langfuse/langfuse-worker` | none | `2g` |

Health: `odctl up` and `odctl recreate` return once `langfuse-web` (`wget -q --spider http://127.0.0.1:3000/api/public/health`) and `langfuse-worker` (`wget -q --spider http://127.0.0.1:3030/api/health`) pass their health checks, so call what the check tests with no wait loop.

Data: `langfuse-web` and `langfuse-worker` keep their data in the `langfuse` database of the `postgres` profile, so `odctl down langfuse` and `odctl recreate langfuse` keep it while `postgres` runs, and `odctl down postgres` loses it.
