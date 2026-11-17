# Profiles

A profile is what `odctl up` starts. These pages are generated from `registry.yml` and the compose files when the site is built.

## [Messaging](https://jaehyeon.me/odctl/latest/profiles/messaging/index.md)

| Profile                                                                         | Technology | Description                                                                               |
| ------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| [`kafka-lite`](https://jaehyeon.me/odctl/latest/profiles/messaging/#kafka-lite) | Kafka      | Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers. |
| [`kafka-full`](https://jaehyeon.me/odctl/latest/profiles/messaging/#kafka-full) | Kafka      | Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers. |

## [Stream and Batch Processing](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/index.md)

| Profile                                                                                           | Technology   | Description                                                                                      |
| ------------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| [`flink-lite`](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/#flink-lite) | Apache Flink | Stateful, real-time stream processing engine. Lite uses 1 TaskManager; Full uses 3 TaskManagers. |
| [`flink-full`](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/#flink-full) | Apache Flink | Stateful, real-time stream processing engine. Lite uses 1 TaskManager; Full uses 3 TaskManagers. |
| [`spark-lite`](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/#spark-lite) | Apache Spark | Distributed batch and micro-batch data processing. Lite uses 1 Worker; Full uses 3 Workers.      |
| [`spark-full`](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/#spark-full) | Apache Spark | Distributed batch and micro-batch data processing. Lite uses 1 Worker; Full uses 3 Workers.      |

## [Analytics](https://jaehyeon.me/odctl/latest/profiles/analytics/index.md)

| Profile                                                                     | Technology | Description                                                                                       |
| --------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------- |
| [`ch-lite`](https://jaehyeon.me/odctl/latest/profiles/analytics/#ch-lite)   | ClickHouse | Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). |
| [`ch-full`](https://jaehyeon.me/odctl/latest/profiles/analytics/#ch-full)   | ClickHouse | Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). |
| [`trino`](https://jaehyeon.me/odctl/latest/profiles/analytics/#trino)       | Trino      | Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). |
| [`metabase`](https://jaehyeon.me/odctl/latest/profiles/analytics/#metabase) | Metabase   | Real-time OLAP database (ClickHouse), Federated SQL engine (Trino), and BI dashboards (Metabase). |

## [Orchestration](https://jaehyeon.me/odctl/latest/profiles/orchestration/index.md)

| Profile                                                                         | Technology     | Description                                                                                                 |
| ------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------- |
| [`airflow`](https://jaehyeon.me/odctl/latest/profiles/orchestration/#airflow)   | Apache Airflow | Workflow orchestration and pipeline scheduling (Airflow), and durable workflows written in code (Temporal). |
| [`temporal`](https://jaehyeon.me/odctl/latest/profiles/orchestration/#temporal) | Temporal       | Workflow orchestration and pipeline scheduling (Airflow), and durable workflows written in code (Temporal). |

## [MLOps](https://jaehyeon.me/odctl/latest/profiles/mlops/index.md)

| Profile                                                                   | Technology | Description                                                                                                               |
| ------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| [`mlflow`](https://jaehyeon.me/odctl/latest/profiles/mlops/#mlflow)       | MLflow     | Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). |
| [`feast`](https://jaehyeon.me/odctl/latest/profiles/mlops/#feast)         | Feast      | Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). |
| [`evidently`](https://jaehyeon.me/odctl/latest/profiles/mlops/#evidently) | Evidently  | Experiment tracking, model registry and model serving (MLflow), the feature store (Feast), and ML monitoring (Evidently). |

## [Metadata and Lineage](https://jaehyeon.me/odctl/latest/profiles/metadata-and-lineage/index.md)

| Profile                                                                                | Technology   | Description                                       |
| -------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------- |
| [`metadata`](https://jaehyeon.me/odctl/latest/profiles/metadata-and-lineage/#metadata) | OpenMetadata | Data catalog, discovery, and governance platform. |
| [`lineage`](https://jaehyeon.me/odctl/latest/profiles/metadata-and-lineage/#lineage)   | Marquez      | System telemetry, monitoring, and data lineage.   |

## [Observability](https://jaehyeon.me/odctl/latest/profiles/observability/index.md)

| Profile                                                                           | Technology                    | Description                                     |
| --------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------- |
| [`telemetry`](https://jaehyeon.me/odctl/latest/profiles/observability/#telemetry) | Telemetry (grafana/otel-lgtm) | System telemetry, monitoring, and data lineage. |

## [Storage and Catalog](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/index.md)

| Profile                                                                               | Technology           | Description                                                                                                                              |
| ------------------------------------------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [`postgres`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#postgres) | PostgreSQL           | PostgreSQL metadata backend.                                                                                                             |
| [`storage`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#storage)   | SeaweedFS            | SeaweedFS S3-compatible object storage.                                                                                                  |
| [`catalog`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#catalog)   | Iceberg REST Catalog | Iceberg REST Catalog.                                                                                                                    |
| [`valkey`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#valkey)     | Valkey               | Stream storage (Fluss) and multi-model data store (Valkey Bundle). Valkey includes advanced JSON, Bloom, and Vector Search capabilities. |
| [`fluss`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#fluss)       | Apache Fluss         | Stream storage (Fluss) and multi-model data store (Valkey Bundle). Valkey includes advanced JSON, Bloom, and Vector Search capabilities. |
| [`deps`](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/#deps)         | Shared Dependencies  | Shared dependencies, JARs, connectors, and Docker network                                                                                |
