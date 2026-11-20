# Guides

Each guide starts the profiles one task needs, then shows how to use their services from the host and from a container. The guides are in groups by area, in the same order as the sidebar. A guide may start from a stack that an earlier guide in its group set up, so the pages of a group read in order.

______________________________________________________________________

## Streaming

| Guide                                                                               | What it shows                                                                                           |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [Kafka](https://jaehyeon.me/odctl/latest/guides/kafka/index.md)                     | the Kafka broker, the schema registry and Kafka UI of `kafka-lite`                                      |
| [Kafka Connect](https://jaehyeon.me/odctl/latest/guides/kafka-connect/index.md)     | the Kafka Connect worker and the connectors it comes with                                               |
| [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/index.md)             | a Flink SQL job, sent through the SQL Gateway, that reads a Kafka topic and writes totals to PostgreSQL |
| [Rolling Windows](https://jaehyeon.me/odctl/latest/guides/rolling-windows/index.md) | features over the last 10 minutes, 1 hour and 1 day, with `OVER` windows                                |
| [Fluss](https://jaehyeon.me/odctl/latest/guides/fluss/index.md)                     | Fluss tables that Flink writes and reads with low latency                                               |

## Lakehouse and Batch

| Guide                                                                                     | What it shows                                                                  |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [Ingest into Iceberg](https://jaehyeon.me/odctl/latest/guides/iceberg-ingestion/index.md) | Kafka Connect, Flink and Spark writing Iceberg tables through one REST catalog |
| [Spark](https://jaehyeon.me/odctl/latest/guides/spark/index.md)                           | Spark jobs on the `iceberg` catalog, and the Spark History Server              |

## Analytics

| Guide                                                                                 | What it shows                                                                                    |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [ClickHouse](https://jaehyeon.me/odctl/latest/guides/clickhouse/index.md)             | a ClickHouse cluster with shards, replicas and ClickHouse Keeper                                 |
| [Trino and Metabase](https://jaehyeon.me/odctl/latest/guides/trino-metabase/index.md) | one SQL interface over PostgreSQL, Iceberg, ClickHouse, Kafka and Valkey, and charts in Metabase |

## Orchestration

| Guide                                                                                 | What it shows                                                                                      |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [Airflow DAGs from S3](https://jaehyeon.me/odctl/latest/guides/airflow-dags/index.md) | Airflow reading DAG files that you upload to SeaweedFS                                             |
| [Temporal Workers](https://jaehyeon.me/odctl/latest/guides/temporal-workers/index.md) | a worker of your own that runs workflows and activities, and a workflow that waits for an approval |

## ML and AI

| Guide                                                                                             | What it shows                                                                           |
| ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [Feast with Iceberg](https://jaehyeon.me/odctl/latest/guides/feast-iceberg/index.md)              | a feature store with its offline store on Iceberg and its online store on Valkey        |
| [Feast Vector Retrieval](https://jaehyeon.me/odctl/latest/guides/feast-vector-retrieval/index.md) | the stored rows whose embeddings are nearest to a query embedding                       |
| [MLflow](https://jaehyeon.me/odctl/latest/guides/mlflow/index.md)                                 | runs and models in the tracking server, and a registered model scored over HTTP         |
| [Evidently Reports](https://jaehyeon.me/odctl/latest/guides/evidently-reports/index.md)           | data drift and data quality reports pushed to the Evidently UI                          |
| [Label Studio](https://jaehyeon.me/odctl/latest/guides/label-studio/index.md)                     | a labelling project, its tasks and labels, and the labels loaded into PostgreSQL        |
| [Hybrid Search](https://jaehyeon.me/odctl/latest/guides/hybrid-search/index.md)                   | vector search and BM25 keyword ranking in PostgreSQL, and their rankings combined       |
| [Valkey](https://jaehyeon.me/odctl/latest/guides/valkey/index.md)                                 | the Valkey Bundle, with its modules for JSON documents, Bloom filters and vector search |
| [Langfuse](https://jaehyeon.me/odctl/latest/guides/langfuse/index.md)                             | traces and evaluations of an application built on an LLM                                |

## Metadata and Operations

| Guide                                                                               | What it shows                                                        |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [OpenLineage and Marquez](https://jaehyeon.me/odctl/latest/guides/lineage/index.md) | OpenLineage events from jobs, and the lineage graph Marquez draws    |
| [OpenMetadata](https://jaehyeon.me/odctl/latest/guides/openmetadata/index.md)       | a data catalogue of the stack's databases, tables and columns        |
| [Telemetry](https://jaehyeon.me/odctl/latest/guides/telemetry/index.md)             | metrics, traces and logs sent with OpenTelemetry and read in Grafana |

The MCP server, which gives an AI assistant odctl's commands as tools, is in [AI Assistants](https://jaehyeon.me/odctl/latest/ai/index.md).
