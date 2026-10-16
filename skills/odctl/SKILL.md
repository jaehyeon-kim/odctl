---
name: odctl
description: Start a local open data stack with odctl and reach its services. Use when a task needs Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, PostgreSQL, SeaweedFS, MLflow, Feast, Evidently, Airflow, Temporal, Marquez, OpenMetadata, Valkey, Fluss or Grafana running locally in Docker.
---

# odctl

odctl starts open source data services as Docker Compose profiles. Install it with `uv tool install odctl` or `pipx install odctl`; it needs Docker. This file is generated from odctl's `registry.yml` and compose files.

## How to use it

- Start what the task needs with `odctl up <profile> [<profile> ...]`. Each profile also starts the profiles it depends on, listed below, and `odctl up` returns once every service is running, and healthy where it has a health check.
- `odctl up <profile> --dry-run` prints the plan without starting anything. `odctl explain <profile>` shows its services, images and dependencies.
- `odctl down <profile>` stops only the profiles named, not their dependencies. Services keep their data inside their containers, so `down` deletes it. Add `--volumes` to also remove named volumes: the shared jar volume `odctl-shared-deps` and Spark's `spark-events-data`. `odctl down --all --volumes` removes everything.
- Every port is published on `127.0.0.1` only, so other machines cannot reach it. From the host, use `127.0.0.1` and the host port. From a container, join the `odctl` Docker network and use the container name and container port, for example `broker-1:19092` or `http://catalog:8181`.
- Logins are in each profile's notes below. Most services use the user `user` and the password `password`; some have no login.
- `odctl init` copies the compose files, `registry.yml` and `.env` into `.odctl/` in the current directory, so they can be edited. Run `odctl recreate <profile>` after editing a compose file or `.env`.
- `-lite` profiles run one node of a tool; `-full` profiles run a cluster of it. Start one of the pair, not both.

## Commands

| Command | Does |
| --- | --- |
| `odctl list` | List all available profiles and their capabilities. |
| `odctl explain` | Explain the details, services, images, and dependencies of a profile. |
| `odctl init` | Initialize a local .odctl workspace for custom configurations. |
| `odctl pull` | Pre-fetch Docker images without starting the containers. |
| `odctl up` | Launch Open Data profiles. |
| `odctl down` | Stop and remove profile containers and networks. |
| `odctl ps` | List Docker containers managed by the Open Data Stack. |
| `odctl info` | Show the installed odctl version and whether Docker is reachable. |
| `odctl logs` | Fetch the logs of containers managed by specific profiles. |
| `odctl restart` | Restart one or more specific profiles. |
| `odctl recreate` | Replace one or more profiles' containers, applying compose file changes. |

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
| `kafka` | `apache/kafka:4.3.1` | `9092:9092` | `1500m` |
| `connect` | `apache/kafka:4.3.1` | `8083:8083` | `2g` |
| `karapace` | `ghcr.io/aiven-open/karapace:6.2.4` | `8081:8081` | `512m` |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui:v1.5.0` | `8086:8080` | `512m` |

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
| `kafka-1` | `apache/kafka:4.3.1` | `9092:9092` | `1500m` |
| `kafka-2` | `apache/kafka:4.3.1` | `9093:9093` | `1500m` |
| `kafka-3` | `apache/kafka:4.3.1` | `9094:9094` | `1500m` |
| `connect` | `apache/kafka:4.3.1` | `8083:8083` | `2g` |
| `karapace` | `ghcr.io/aiven-open/karapace:6.2.4` | `8081:8081` | `512m` |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui:v1.5.0` | `8086:8080` | `512m` |

## Stream and batch processing

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
| `jobmanager` | `flink:2.2-java17` | `8082:8081` | `1500m` |
| `taskmanager-a` | `flink:2.2-java17` | none | `3500m` |
| `sql-gateway` | `flink:2.2-java17` | `8084:8083` | `1g` |

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
| `jobmanager` | `flink:2.2-java17` | `8082:8081` | `1500m` |
| `taskmanager-a` | `flink:2.2-java17` | none | `3500m` |
| `taskmanager-b` | `flink:2.2-java17` | none | `3500m` |
| `taskmanager-c` | `flink:2.2-java17` | none | `3500m` |
| `sql-gateway` | `flink:2.2-java17` | `8084:8083` | `1g` |

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
| `spark-master` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9080:8080`, `7077:7077` | `1g` |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9081:8081` | `2g` |
| `spark-history` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `18080:18080` | `1g` |

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
| `spark-master` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9080:8080`, `7077:7077` | `1g` |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9081:8081` | `2g` |
| `spark-worker-2` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9082:8081` | `2g` |
| `spark-worker-3` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9083:8081` | `2g` |
| `spark-history` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `18080:18080` | `1g` |

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
| `ch-keeper` | `clickhouse/clickhouse-keeper:25.12-alpine` | `9181:9181` | `512m` |
| `ch-shard2-stub` | `alpine:3.24` | none | `64m` |
| `ch-11` | `clickhouse/clickhouse-server:25.12-alpine` | `8123:8123`, `9000:9000` | `4g` |
| `ch-12` | `clickhouse/clickhouse-server:25.12-alpine` | `8124:8123`, `9001:9000` | `4g` |

### ch-full

ClickHouse: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up ch-full` also starts: `deps`.

```text
• ClickHouse HTTP (Shards 1 & 2 / Replicas 1 & 2):
  * External (host): http://127.0.0.1:8123, http://127.0.0.1:8124, http://127.0.0.1:8125, http://127.0.0.1:8126
  * Internal (Docker): http://ch-11:8123, http://ch-12:8123, http://ch-21:8123, http://ch-22:8123
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `ch-keeper` | `clickhouse/clickhouse-keeper:25.12-alpine` | `9181:9181` | `512m` |
| `ch-11-full` | `clickhouse/clickhouse-server:25.12-alpine` | `8123:8123`, `9000:9000` | `4g` |
| `ch-12-full` | `clickhouse/clickhouse-server:25.12-alpine` | `8124:8123`, `9001:9000` | `4g` |
| `ch-21` | `clickhouse/clickhouse-server:25.12-alpine` | `8125:8123`, `9002:9000` | `4g` |
| `ch-22` | `clickhouse/clickhouse-server:25.12-alpine` | `8126:8123`, `9003:9000` | `4g` |

### trino

Trino: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up trino` also starts: `deps`, `postgres`.

```text
• Trino UI & JDBC connection (no password: no authenticator is
  configured, so any username is accepted):
  * External (host): http://127.0.0.1:8080
  * Internal (Docker): http://trino:8080
• Identities: `docker exec -it trino trino` connects as `trino`, the
  CLI default. Pass `--user user` for the stack-wide convention, or
  `--user analyst`, which trino/rules.json denies schema ownership
  while leaving every table privilege in place.
• Catalogs: postgres works with the trino profile alone. iceberg,
  kafka, clickhouse and valkey load without their backing services,
  so they appear in SHOW CATALOGS and then fail at query time unless
  catalog, storage, kafka-lite, ch-lite or valkey is also up.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `trino` | `trinodb/trino:483` | `8080:8080` | `4g` |

### metabase

Metabase: Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). `odctl up metabase` also starts: `deps`, `postgres`.

```text
• Metabase Dashboard Engine:
  * External (host): http://127.0.0.1:3000
  * Internal (Docker): http://metabase:3000
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `metabase` | `metabase/metabase:v0.63.19.3` | `3000:3000` | `1500m` |

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
| `airflow` | `ghcr.io/jaehyeon-kim/odctl/airflow:<CLI version>` | `8085:8080` | `3g` |

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
| `temporal` | `temporalio/temporal:1.9.1` | `7233:7233`, `8233:8233` | `1g` |

## MLOps

### mlflow

MLflow: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). `odctl up mlflow` also starts: `deps`, `postgres`, `storage`.

```text
• MLflow Tracking UI & Artifact Registry Server:
  * External (host): http://127.0.0.1:5004
  * Internal (Docker): http://mlflow:5000
• MLflow Model Scoring Server, idle until MODEL_URI in .env names a model;
  run `odctl up mlflow` again after setting it:
  * External (host): http://127.0.0.1:5003/invocations
  * Internal (Docker): http://mlflow-serve:5003/invocations
• Liveness: http://127.0.0.1:5003/ping and http://127.0.0.1:5003/health
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `mlflow` | `ghcr.io/jaehyeon-kim/odctl/mlflow:<CLI version>` | `5004:5000` | `2500m` |
| `mlflow-serve` | `ghcr.io/jaehyeon-kim/odctl/mlflow:<CLI version>` | `5003:5003` | `1500m` |

### feast

Feast: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). `odctl up feast` also starts: `catalog`, `deps`, `postgres`, `storage`, `valkey`.

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
• Liveness: http://127.0.0.1:6566/health
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `feast-ui` | `quay.io/feastdev/feature-server:0.66.0` | `8890:8888` | `1g` |
| `feast-serve` | `quay.io/feastdev/feature-server:0.66.0` | `6566:6566` | `1g` |

### evidently

Evidently: Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). `odctl up evidently` also starts: `deps`, `postgres`.

```text
• Evidently UI & API (no login, and writes are open):
  * External (host): http://127.0.0.1:8089
  * Internal (Docker): http://evidently:8000
• Push reports with RemoteWorkspace("http://127.0.0.1:8089") from the
  host, or RemoteWorkspace("http://evidently:8000") from a container.
  Reports are computed by the client, so it needs evidently==0.7.23.
  In Airflow, set _AIRFLOW_PIP_DEPS="evidently==0.7.23" in .env.
• Projects, reports, dashboards and datasets: the evidently database
  on Postgres.
• Settings: evidently/config.yaml in the workspace.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `evidently` | `evidently/evidently-service:0.7.23` | `8089:8000` | `1g` |

## Metadata and lineage

### metadata

OpenMetadata: Data catalog, discovery, and governance platform. `odctl up metadata` also starts: `deps`, `postgres`.

```text
• OpenMetadata UI & REST API:
  - External (host): http://127.0.0.1:8585
  - Internal (Docker): http://openmetadata-server:8585
• Ingestion Pipeline UI:
  - External (host): http://127.0.0.1:8087
  - Internal (Docker): http://openmetadata-ingestion:8080
• Default Admin: admin@open-data.local / admin
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `openmetadata-es` | `docker.elastic.co/elasticsearch/elasticsearch:9.3.0` | `9200:9200`, `9300:9300` | `2g` |
| `openmetadata-migrate` | `docker.getcollate.io/openmetadata/server:2.0.1` | none | `1g` |
| `openmetadata-server` | `docker.getcollate.io/openmetadata/server:2.0.1` | `8585:8585`, `8586:8586` | `2g` |
| `openmetadata-ingestion` | `docker.getcollate.io/openmetadata/ingestion:2.0.1` | `8087:8080` | `1500m` |

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
| `marquez-api` | `marquezproject/marquez:0.51.1` | `5002:5000`, `5001:5001` | `1g` |
| `marquez-web` | `marquezproject/marquez-web:0.51.1` | `3003:3000` | `512m` |

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
• OTLP Receiver (metrics, traces and logs):
  * External (host): 127.0.0.1:4317 (gRPC), http://127.0.0.1:4318 (HTTP)
  * Internal (Docker): otel-lgtm:4317 (gRPC), http://otel-lgtm:4318 (HTTP)
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `otel-lgtm` | `grafana/otel-lgtm:0.35.0` | `19090:9090`, `3004:3000`, `4317:4317`, `4318:4318` | `2g` |

## Storage and catalog

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
| `postgres` | `ghcr.io/jaehyeon-kim/odctl/postgres:<CLI version>` | `5432:5432` | `1g` |

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
| `seaweed` | `chrislusf/seaweedfs:4.48` | `8333:8333`, `8889:8888`, `9333:9333` | `512m` |
| `seaweed-init` | `chrislusf/seaweedfs:4.48` | none | not set |

### catalog

Iceberg REST catalog: Iceberg REST Catalog. `odctl up catalog` also starts: `deps`, `postgres`, `storage`.

```text
• REST API Endpoint:
  - External (host): http://127.0.0.1:8181
  - Internal (Docker): http://catalog:8181
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `catalog` | `azul/zulu-openjdk:17-jre-headless` | `8181:8181` | `512m` |

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
| `valkey` | `valkey/valkey-bundle:9.1.3-alpine` | `6379:6379` | `512m` |

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
| `fluss-zookeeper` | `zookeeper:3.9.6` | none | `512m` |
| `fluss-coordinator` | `apache/fluss:1.0.0` | `9123:9123` | `1g` |
| `fluss-tablet-1` | `apache/fluss:1.0.0` | `9124:9123` | `2g` |

### deps

Shared dependencies: Shared dependencies, JARs, connectors, and Docker network `odctl up deps` also starts: nothing else.

```text
• Runs automatically on 'odctl up'.
• No persistent UI or ports exposed.
```

| Service | Image | Host:container ports | Memory limit |
| --- | --- | --- | --- |
| `init-deps` | `ghcr.io/jaehyeon-kim/odctl/deps:<CLI version>` | none | not set |
