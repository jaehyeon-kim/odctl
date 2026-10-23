# Why odctl

I like building demo apps, and each one needs a local environment to try things in. Docker and Docker Compose are good for that. Across several projects, though, it is not easy, and the setup drifts from one project to the next.

odctl is a CLI that manages Docker Compose services. It runs Compose files and selects services with Compose profiles. For one small project with two or three services, plain Compose is fine.

It starts to hurt when you have several projects. One needs Kafka, Flink and Iceberg. Another needs Spark and Trino but not Kafka. Each project ends up with its own Compose file, and over time they drift apart, for example when you upgrade image tags in one and forget the others. With odctl, the files live in one place. Each release fixes the image versions, and an end-to-end test runs every profile before it is published. A project just pins an odctl version.

The second part is the wiring, and odctl does it for you. When PostgreSQL first starts, it creates a database for each service that needs one, such as the Iceberg catalog, Airflow and MLflow. The Iceberg REST catalog keeps its tables in S3 storage (SeaweedFS), and Spark and Trino are already configured to use it. Kafka Connect, Flink and Spark also need connector jars with matching versions. odctl builds them once into a shared image, and each service takes the jars it needs from there. `odctl up spark-lite` starts PostgreSQL, the storage, the catalog and the shared jars first, and Prometheus already scrapes Kafka, Flink, Spark and ClickHouse.

The third part is day-to-day use. With several Compose files, it is hard to remember what is running and where. odctl has commands for that:

- `odctl list` shows every profile and what it runs.
- `odctl explain spark-lite` shows a profile's services, images, ports and the profiles it depends on.
- `odctl up spark-lite --dry-run` shows what would start, in order, before anything starts.
- `odctl ps --all` lists the running containers and their ports.
- `odctl logs spark-lite` shows the logs of one profile.
- `odctl down --all` stops everything.

Getting all of this right by hand takes time, and it is easy to break across projects.

I use odctl in my own projects: [desflow](https://jaehyeon.me/desflow/) starts the services of its tests and examples with it, and so do the demos in [benchtop](https://github.com/jaehyeon-kim/benchtop). It is useful for three kinds of project:

- **Data engineering.** Streaming and batch pipelines on Kafka, Kafka Connect, Flink, Fluss and Spark, an Iceberg lakehouse queried with Trino, ClickHouse for analytics, Airflow and Temporal to run them, and lineage in Marquez and OpenMetadata.
- **ML and MLOps.** MLflow tracks experiments, registers models and serves them. Feast serves features from Iceberg tables and Valkey, and Evidently stores drift reports. The Airflow image has the MLflow and Feast clients, with the tracking URI and the Feast registry already set.
- **AI.** PostgreSQL has pgvector and pg_textsearch for [hybrid search](../guides/hybrid-search.md), and Valkey has vector search. An AI assistant can choose a profile and reach its services with the odctl skill and `llms.txt`, as [Getting started](../getting-started.md#use-it-with-an-ai-assistant) describes. The [Roadmap](roadmap.md) adds an MCP server for AI agents, a Langfuse profile for tracing LLM and agent applications, and a desflow server profile after desflow 1.0.
