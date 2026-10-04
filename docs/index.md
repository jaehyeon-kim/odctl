# Open Data Stack (odctl)

odctl is a command-line tool that runs an open data stack on your machine with Docker Compose. You name the profiles you want, such as `kafka-lite` or `airflow`, and odctl starts them together with the services they depend on.

![odctl architecture](assets/diagram.png)

## What it runs

| Area | Technologies |
| --- | --- |
| Messaging | Kafka (KRaft), Karapace schema registry, Kafka Connect, Kafka UI (kafbat) |
| Stream and batch processing | Apache Flink, Apache Spark |
| Analytics | ClickHouse, Trino, Metabase |
| Orchestration | Apache Airflow, Temporal |
| MLOps | MLflow, Feast, Evidently |
| Metadata and lineage | OpenMetadata, Marquez |
| Observability | grafana/otel-lgtm (OpenTelemetry Collector, Prometheus, Tempo, Loki, Grafana) |
| Storage and catalog | PostgreSQL 18 with pgvector, pg_textsearch and PostGIS, SeaweedFS (S3), Iceberg REST catalog, Valkey Bundle, Apache Fluss |

Kafka Connect ships with the Apache Iceberg sink, the Debezium PostgreSQL source, the ClickHouse sink, the Aiven JDBC and S3 sinks, a Redis connector and the MSK data generator.

## Where to go next

- [Getting started](getting-started.md) installs odctl and starts a first profile.
- [Profiles](profiles/index.md) lists every profile with its ports, images and memory limits.
- [Guides](guides/iceberg-ingestion.md) show how to use the services together.
