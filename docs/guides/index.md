# Guides

Each guide starts the profiles one task needs, then shows how to use their services from the host and from a container. The guides are in groups by area, in the same order as the sidebar. A guide may start from a stack that an earlier guide in its group set up, so the pages of a group read in order.

---

<div class="same-columns" markdown>

## Streaming

| Guide | What it shows |
|---|---|
| [Kafka](kafka.md) | the Kafka broker, the schema registry and Kafka UI of `kafka-lite` |
| [Kafka Connect](kafka-connect.md) | the Kafka Connect worker and the connectors it comes with |
| [Flink SQL](flink-sql.md) | a Flink SQL job, sent through the SQL Gateway, that reads a Kafka topic and writes totals to PostgreSQL |
| [Rolling Windows](rolling-windows.md) | features over the last 10 minutes, 1 hour and 1 day, with `OVER` windows |
| [Fluss](fluss.md) | Fluss tables that Flink writes and reads with low latency |

## Lakehouse and Batch

| Guide | What it shows |
|---|---|
| [Ingest into Iceberg](iceberg-ingestion.md) | Kafka Connect, Flink and Spark writing Iceberg tables through one REST catalog |
| [Spark](spark.md) | Spark jobs on the `iceberg` catalog, and the Spark History Server |

## Analytics

| Guide | What it shows |
|---|---|
| [ClickHouse](clickhouse.md) | a ClickHouse cluster with shards, replicas and ClickHouse Keeper |
| [Trino and Metabase](trino-metabase.md) | one SQL interface over PostgreSQL, Iceberg, ClickHouse, Kafka and Valkey, and charts in Metabase |

## Orchestration

| Guide | What it shows |
|---|---|
| [Airflow DAGs from S3](airflow-dags.md) | Airflow reading DAG files that you upload to SeaweedFS |
| [Temporal Workers](temporal-workers.md) | a worker of your own that runs workflows and activities, and a workflow that waits for an approval |

## ML and AI

| Guide | What it shows |
|---|---|
| [Feast with Iceberg](feast-iceberg.md) | a feature store with its offline store on Iceberg and its online store on Valkey |
| [Feast Vector Retrieval](feast-vector-retrieval.md) | the stored rows whose embeddings are nearest to a query embedding |
| [MLflow](mlflow.md) | runs and models in the tracking server, and a registered model scored over HTTP |
| [Evidently Reports](evidently-reports.md) | data drift and data quality reports pushed to the Evidently UI |
| [Label Studio](label-studio.md) | a labelling project, its tasks and labels, and the labels loaded into PostgreSQL |
| [Hybrid Search](hybrid-search.md) | vector search and BM25 keyword ranking in PostgreSQL, and their rankings combined |
| [Valkey](valkey.md) | the Valkey Bundle, with its modules for JSON documents, Bloom filters and vector search |
| [Langfuse](langfuse.md) | traces and evaluations of an application built on an LLM |

## Metadata and Operations

| Guide | What it shows |
|---|---|
| [OpenLineage and Marquez](lineage.md) | OpenLineage events from jobs, and the lineage graph Marquez draws |
| [OpenMetadata](openmetadata.md) | a data catalogue of the stack's databases, tables and columns |
| [Telemetry](telemetry.md) | metrics, traces and logs sent with OpenTelemetry and read in Grafana |

</div>

The MCP server, which gives an AI assistant odctl's commands as tools, is in [AI Assistants](../ai/index.md).
