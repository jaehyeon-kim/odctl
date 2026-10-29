# Open Data Stack (odctl)

**Run an open data stack on your machine, with its services already connected, from one command.**

odctl is a command-line tool that runs an open data stack on your machine with Docker Compose. You name the [profiles](https://jaehyeon.me/odctl/latest/how-it-works/#profiles) you want, such as `kafka-lite` or `airflow`, and odctl starts them together with the services they depend on.

A Compose file of your own is enough for one small project. [Why odctl](https://jaehyeon.me/odctl/latest/about/why-odctl/index.md) explains what odctl adds when several projects need different parts of the stack.

## Commands

Each command has its own section in the CLI reference, with its options and examples. The Example column links to a page that runs the command and shows its output, and [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md) runs them in order on one profile.

| Command                                                                  | Use it to                                                                    | Example                                                                                  |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [`odctl list`](https://jaehyeon.me/odctl/latest/cli/#odctl-list)         | See every profile and what it runs                                           | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile)     |
| [`odctl explain`](https://jaehyeon.me/odctl/latest/cli/#odctl-explain)   | See a profile's services, images, ports and the profiles it depends on       | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile)     |
| [`odctl ps`](https://jaehyeon.me/odctl/latest/cli/#odctl-ps)             | See the running containers, their health and their ports                     | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl info`](https://jaehyeon.me/odctl/latest/cli/#odctl-info)         | Check the installed odctl version and whether Docker is reachable            | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl init`](https://jaehyeon.me/odctl/latest/cli/#odctl-init)         | Copy the compose files and settings into `.odctl`, so you can edit them      | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#create-a-workspace)  |
| [`odctl pull`](https://jaehyeon.me/odctl/latest/cli/#odctl-pull)         | Download a profile's images before you start it                              | [How It Works](https://jaehyeon.me/odctl/latest/how-it-works/#which-images-run)          |
| [`odctl up`](https://jaehyeon.me/odctl/latest/cli/#odctl-up)             | Start profiles and the profiles they depend on                               | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile)     |
| [`odctl down`](https://jaehyeon.me/odctl/latest/cli/#odctl-down)         | Stop profiles and remove their containers                                    | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#stop-a-profile)      |
| [`odctl logs`](https://jaehyeon.me/odctl/latest/cli/#odctl-logs)         | Read the logs of a profile's containers                                      | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl restart`](https://jaehyeon.me/odctl/latest/cli/#odctl-restart)   | Restart a profile's containers and keep them                                 | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#restart-a-profile)   |
| [`odctl recreate`](https://jaehyeon.me/odctl/latest/cli/#odctl-recreate) | Replace a profile's containers, to apply an edit to a compose file or `.env` | [How It Works](https://jaehyeon.me/odctl/latest/how-it-works/#examples)                  |

## What It Runs

| Area                                                                                                          | Technologies                                                                                                              |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [Messaging](https://jaehyeon.me/odctl/latest/profiles/messaging/index.md)                                     | Kafka (KRaft), Karapace schema registry, Kafka Connect, Kafka UI (kafbat)                                                 |
| [Stream and Batch Processing](https://jaehyeon.me/odctl/latest/profiles/stream-and-batch-processing/index.md) | Apache Flink, Apache Spark                                                                                                |
| [Analytics](https://jaehyeon.me/odctl/latest/profiles/analytics/index.md)                                     | ClickHouse, Trino, Metabase                                                                                               |
| [Orchestration](https://jaehyeon.me/odctl/latest/profiles/orchestration/index.md)                             | Apache Airflow, Temporal                                                                                                  |
| [MLOps](https://jaehyeon.me/odctl/latest/profiles/mlops/index.md)                                             | MLflow, Feast, Evidently                                                                                                  |
| [Metadata and Lineage](https://jaehyeon.me/odctl/latest/profiles/metadata-and-lineage/index.md)               | OpenMetadata, Marquez                                                                                                     |
| [Observability](https://jaehyeon.me/odctl/latest/profiles/observability/index.md)                             | grafana/otel-lgtm (OpenTelemetry Collector, Prometheus, Tempo, Loki, Grafana)                                             |
| [Storage and Catalog](https://jaehyeon.me/odctl/latest/profiles/storage-and-catalog/index.md)                 | PostgreSQL 18 with pgvector, pg_textsearch and PostGIS, SeaweedFS (S3), Iceberg REST catalog, Valkey Bundle, Apache Fluss |

Kafka Connect comes with a set of connectors, such as the Iceberg sink and the Debezium PostgreSQL source. [Kafka Connect](https://jaehyeon.me/odctl/latest/guides/kafka-connect/index.md) lists them all.

## Where to Go Next

- [Why odctl](https://jaehyeon.me/odctl/latest/about/why-odctl/index.md) says why odctl exists and what it is for.
- [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md) installs odctl and starts a first profile.
- [Profiles](https://jaehyeon.me/odctl/latest/profiles/index.md) lists every profile with its ports, images and memory limits.
- [Guides](https://jaehyeon.me/odctl/latest/guides/kafka/index.md) show how to use each service, starting with Kafka.

## Projects That Use odctl

- [benchtop](https://github.com/jaehyeon-kim/benchtop): data engineering and machine learning projects, each run from a cold clone on odctl.
- [desflow](https://github.com/jaehyeon-kim/desflow) ([docs](https://jaehyeon.me/desflow/)): a SimPy library for simulations that stream to Kafka, PostgreSQL, Redis and Iceberg.
- [agentic-analytics-system](https://github.com/jaehyeon-kim/agentic-analytics-system): conversational analytics over an Iceberg lakehouse.

Blog posts about odctl and these projects are tagged [odctl](https://jaehyeon.me/tags/odctl/) on jaehyeon.me.
