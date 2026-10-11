# Open Data Stack (odctl)

odctl is a command-line tool that runs an open data stack on your machine with Docker Compose. You name the profiles you want, such as `kafka-lite` or `airflow`, and odctl starts them together with the services they depend on.

## Why not plain Docker Compose?

odctl is Docker Compose: it runs Compose files and selects services with Compose profiles. For one small project with two or three services, a Compose file of your own is enough. odctl helps when there are more.

- **One set of files for every project.** Projects need different tools. One uses MLflow, Feast and Airflow, and another does not need Airflow. Copied compose files drift apart, for example when an image is upgraded in one copy only. odctl keeps the files in one place. Each release fixes the image versions and runs an end-to-end test for every profile, so a project pins an odctl version instead of keeping its own files.
- **The services are already connected.** PostgreSQL creates the databases for MLflow, Feast and the others when it first starts. MLflow keeps its artifacts in S3 storage. Feast's config points to its registry in PostgreSQL, to Iceberg for offline features and to Valkey for online features. The Airflow image has the MLflow and Feast clients installed. Kafka Connect, Flink and Spark take connector jars with matching versions from one shared image.
- **Commands show what is running.** `odctl explain` shows a profile's services, ports and dependencies. `odctl up --dry-run` shows what would start, in order. `odctl ps` lists the running containers with their health and ports. The [CLI reference](https://jaehyeon.me/odctl/latest/cli/index.md) lists every command.

## What it runs

| Area                                                                                                          | Technologies                                                                                                              |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [Messaging](https://jaehyeon.me/odctl/latest/profiles/messaging/index.md)                                     | Kafka (KRaft), Karapace schema registry, Kafka Connect, Kafka UI (kafbat)                                                 |
| [Stream and batch processing](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/index.md) | Apache Flink, Apache Spark                                                                                                |
| [Analytics](https://jaehyeon.me/odctl/latest/profiles/analytics/index.md)                                     | ClickHouse, Trino, Metabase                                                                                               |
| [Orchestration](https://jaehyeon.me/odctl/latest/profiles/orchestration/index.md)                             | Apache Airflow, Temporal                                                                                                  |
| [MLOps](https://jaehyeon.me/odctl/latest/profiles/mlops/index.md)                                             | MLflow, Feast, Evidently                                                                                                  |
| [Metadata and lineage](https://jaehyeon.me/odctl/latest/profiles/metadata-and-lineage/index.md)               | OpenMetadata, Marquez                                                                                                     |
| [Observability](https://jaehyeon.me/odctl/latest/profiles/observability/index.md)                             | grafana/otel-lgtm (OpenTelemetry Collector, Prometheus, Tempo, Loki, Grafana)                                             |
| [Storage and catalog](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/index.md)                 | PostgreSQL 18 with pgvector, pg_textsearch and PostGIS, SeaweedFS (S3), Iceberg REST catalog, Valkey Bundle, Apache Fluss |

Kafka Connect comes with a set of connectors, such as the Iceberg sink and the Debezium PostgreSQL source. [Kafka Connect](https://jaehyeon.me/odctl/latest/guides/kafka-connect/index.md) lists them all.

## Where to go next

- [Getting started](https://jaehyeon.me/odctl/latest/getting-started/index.md) installs odctl and starts a first profile.
- [Profiles](https://jaehyeon.me/odctl/latest/profiles/index.md) lists every profile with its ports, images and memory limits.
- [Guides](https://jaehyeon.me/odctl/latest/guides/iceberg-ingestion/index.md) show how to use the services together.

## Projects that use odctl

- [benchtop](https://github.com/jaehyeon-kim/benchtop): small data engineering and machine learning projects, each run from a cold clone on odctl.
- [dynamic-des](https://github.com/jaehyeon-kim/dynamic-des): a SimPy library for simulations that stream to Kafka, PostgreSQL, Redis and Iceberg.
- [agentic-analytics-system](https://github.com/jaehyeon-kim/agentic-analytics-system): conversational analytics over an Iceberg lakehouse.

Blog posts about odctl and these projects are tagged [odctl](https://jaehyeon.me/tags/odctl/) on jaehyeon.me.
