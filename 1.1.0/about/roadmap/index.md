# Roadmap

The work comes in the order shown, without dates: a release ships when it is ready. The timeline marks the work in progress and what follows it: features first, then the testing and setup work that adds no feature. Each planned item links to its GitHub issue.

## Now and next

Localhost-only services

In 1.1.0: every service is reachable from your machine only, and the docs have this Roadmap and a [Changelog](https://jaehyeon.me/odctl/latest/about/changelog/index.md).

Streaming

Flink writes to HTTP APIs such as Feast's push endpoint, Spark reads Kafka without downloading packages, and a guide to Kafka retention. [#151](https://github.com/jaehyeon-kim/odctl/issues/151)

Feast

An MCP endpoint for agents, pushing streaming features and materialising from Airflow, and vector retrieval on PostgreSQL. [#150](https://github.com/jaehyeon-kim/odctl/issues/150)

OpenMetadata connectors and Kafka schemas

A Python connector uploaded to S3 is picked up by OpenMetadata, the way the `airflow` profile picks up DAGs, and extra packages can be installed in the ingestion container. Kafka topics whose producers use no schema registry get their fields from JSON Schemas registered in Karapace, with no producer change. [#148](https://github.com/jaehyeon-kim/odctl/issues/148)

Stable interface and JSON output

A written list of what 1.x keeps stable: profile names, ports, `.env` keys, volumes and the workspace files. `--json` on `list`, `explain`, `ps` and `info`, and `--yes` on `init` and `down` for scripts. [#140](https://github.com/jaehyeon-kim/odctl/issues/140)

MCP server

Tools for AI agents that show the profiles and what is running, with `up` and `down` behind a setting. [#141](https://github.com/jaehyeon-kim/odctl/issues/141)

## Later

The work after that, in the order it is planned.

- **Langfuse**

  ______________________________________________________________________

  A profile for tracing and evaluating LLM and agent applications, using odctl's ClickHouse.

  [#120](https://github.com/jaehyeon-kim/odctl/issues/120)

- **desflow server**

  ______________________________________________________________________

  After desflow 1.0, when its server ships: A profile that runs the [desflow](https://jaehyeon.me/desflow/) simulation server, so a project can start simulations that write to Kafka, PostgreSQL or Iceberg.

  [#144](https://github.com/jaehyeon-kim/odctl/issues/144)

- **Snapshot and restore**

  ______________________________________________________________________

  `odctl snapshot` and `odctl restore` save a profile's data and bring it back, so a lab or an agent can start again from a known state.

  [#142](https://github.com/jaehyeon-kim/odctl/issues/142)

- **Lineage and alerts**

  ______________________________________________________________________

  Lineage from Airflow, Spark and Feast in Marquez, and Grafana alert rules, starting with one for a failed DAG run.

  [#149](https://github.com/jaehyeon-kim/odctl/issues/149)

- **Kafka Connect transforms**

  ______________________________________________________________________

  Transforms built into the Connect image: make a record schema required, replace personal fields with a hash, and send lineage events to Marquez for any connector.

  [#143](https://github.com/jaehyeon-kim/odctl/issues/143)

- **Testing and CI**

  ______________________________________________________________________

  The end-to-end tests run on every pull request, including image updates, so an update is tested before it merges. Each release is also tested as an upgrade from the one before it, and on arm64, which most Macs run. A pull request then tests only the profiles it changes, and the full suite runs every night.

  [#102](https://github.com/jaehyeon-kim/odctl/issues/102)

- **Memory check**

  ______________________________________________________________________

  `odctl up` warns when Docker has less memory than the profiles it starts need.

  [#155](https://github.com/jaehyeon-kim/odctl/issues/155)

- **Models on the host**

  ______________________________________________________________________

  One setting lets containers reach a model server on the host with an OpenAI-compatible API, such as Ollama or LM Studio, on macOS, Linux and WSL2.

  [#109](https://github.com/jaehyeon-kim/odctl/issues/109)

## Alongside

Work that does not wait for a release, published as it is ready.

- **Labs**

  ______________________________________________________________________

  A series in seven parts that takes one generated dataset of web events and logs through Kafka, Flink, ClickHouse, Spark, Trino and the MLOps tools, each lab listed on the [Labs](https://jaehyeon.me/odctl/latest/labs/index.md) page as it is published.

  [benchtop #1](https://github.com/jaehyeon-kim/benchtop/issues/1)

- **Guides**

  ______________________________________________________________________

  Iceberg table maintenance with Spark, vector search in Valkey, and traces and prompts in MLflow.

  [#152](https://github.com/jaehyeon-kim/odctl/issues/152)
