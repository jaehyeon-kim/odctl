# Roadmap

The work comes in the order shown, without dates: a release ships when it is ready. Features come first, then the testing and setup work that adds no feature. Each planned item links to its GitHub issue where one exists.

## Next Releases

1.5.0: Stable interface and JSON output

A written list of what 1.x keeps stable: profile names, ports, `.env` keys, volumes and the workspace files. `--json` on `list`, `explain`, `ps` and `info`, and `--yes` on `init` and `down` for scripts. [#140](https://github.com/jaehyeon-kim/odctl/issues/140)

1.6.0: MCP server

Tools for AI agents that show the profiles and what is running, with `up` and `down` behind a setting. The dry run of `odctl down --volumes` names the volumes it would remove. [#141](https://github.com/jaehyeon-kim/odctl/issues/141), [#170](https://github.com/jaehyeon-kim/odctl/issues/170)

1.7.0: Langfuse

A profile for tracing and evaluating LLM and agent applications, using odctl's ClickHouse. [#120](https://github.com/jaehyeon-kim/odctl/issues/120)

1.8.0: Lineage and alerts

Lineage from Airflow, Spark and Feast in Marquez, and Grafana alert rules, starting with one for a failed DAG run. [#149](https://github.com/jaehyeon-kim/odctl/issues/149)

1.9.0: Kafka Connect transforms

Transforms built into the Connect image: make a record schema required, replace personal fields with a hash, and send lineage events to Marquez for any connector. [#143](https://github.com/jaehyeon-kim/odctl/issues/143)

1.10.0: Memory check and models on the host

`odctl up` warns when Docker has less memory than the profiles it starts need. One setting lets containers reach a model server on the host with an OpenAI-compatible API, such as Ollama or LM Studio, on macOS, Linux and WSL2. The guide also covers the Ollama embeddings route, batch embedding in Airflow and a hand-run rerank server. [#155](https://github.com/jaehyeon-kim/odctl/issues/155), [#109](https://github.com/jaehyeon-kim/odctl/issues/109)

MLOps guides

Guides for a prediction log and labels in PostgreSQL, feature and leakage checks, hyperparameter search, ONNX quantisation, serving a second model or many models, serving latency sent over OTLP, Feast dataset versions and reads of large Iceberg tables. No new service and no new version: the guides are published when they reach `main`.

Agents guides

Guides for traces, token metrics, feedback and evaluation of agent and model calls, an agent in a Temporal workflow, agent services beside the stack, and agent state in PostgreSQL. No new service and no new version.

Retrieval guides

Guides for hybrid search with rank fusion, graph queries in PostgreSQL, ingestion with change detection, Valkey as a cache, and media with signed URLs. No new service and no new version.

1.11.0: Label Studio

A `label-studio` profile for labelling data by hand, on odctl's PostgreSQL. Its guide loads the exported labels into the label table of the MLOps guides. [#169](https://github.com/jaehyeon-kim/odctl/issues/169)

## Alongside

Work that does not wait for a release, published as it is ready.

- **Guides**

  ______________________________________________________________________

  Iceberg table maintenance with Spark, vector search in Valkey, and traces and prompts in MLflow.

  [#152](https://github.com/jaehyeon-kim/odctl/issues/152)

- **Testing and CI**

  ______________________________________________________________________

  It lands between 1.9.0 and 1.10.0. It changes only the tests, the CI workflows, the dependency update settings and two docs pages, not odctl itself, so it has no version of its own. The end-to-end tests run on every pull request, including image updates, so an update is tested before it merges. Each release is also tested as an upgrade from the one before it, and on arm64, which most Macs run. A pull request then tests only the profiles it changes, and the full suite runs every night. The CI user guide and the per-task environments section are published with 1.10.0.

  [#102](https://github.com/jaehyeon-kim/odctl/issues/102)

## After desflow 1.0

- **desflow server**

  ______________________________________________________________________

  When the desflow server ships: a profile that runs the [desflow](https://jaehyeon.me/desflow/) simulation server, so a project can start simulations that write to Kafka, PostgreSQL or Iceberg.

  [#144](https://github.com/jaehyeon-kim/odctl/issues/144)

## Released

Newest first.

1.4.0: Feast

Feast's feature server serves an MCP endpoint for agents, the Feast guide pushes features over HTTP and from Flink SQL and materialises from an Airflow DAG, and a new guide retrieves the nearest documents from PostgreSQL with pgvector. The `metadata` e2e group is split into three that run in parallel. [#150](https://github.com/jaehyeon-kim/odctl/issues/150), [#168](https://github.com/jaehyeon-kim/odctl/issues/168)

1.3.0: OpenMetadata connectors

Custom OpenMetadata connectors uploaded to S3 are picked up by the ingestion container with no restart, AutoPilot is off by default, extra packages can be installed in the ingestion container, and OpenMetadata runs 2.0.7.

1.2.2: newer images

Trino, Metabase, `otel-lgtm` and the PostgreSQL JDBC driver in the deps image are updated, and the Grafana dashboard descriptions no longer name the exact version of the component they show.

1.2.1: recreate on several files

`odctl recreate`, `odctl restart` and `odctl logs` work on profiles from more than one compose file, `odctl init` and `odctl down` can skip their prompt, and the docs show every command with a runnable example.

1.2.0: Streaming

Flink writes to HTTP APIs such as Feast's push endpoint, Spark reads Kafka without downloading packages, and new guides cover Kafka retention and several rolling windows in Flink SQL. The release also fixes the MLflow and storage guides and sets `GOMEMLIMIT`, a soft limit for the Go runtime, on `seaweed`, so large model uploads do not hit its container memory limit.

1.1.0: localhost-only services

Every service is reachable from your machine only, Kafka no longer publishes the minikube listener ports, an odctl skill and `llms.txt` help AI assistants, and the docs have this Roadmap and a [Changelog](https://jaehyeon.me/odctl/latest/about/changelog/index.md).

1.0.2: Python 3.15

odctl is tested on Python 3.15, ZooKeeper and Metabase are updated, and Renovate groups image updates by compose file.

1.0.1: upgrade fixes

Old jars no longer stay in the shared deps volume after an upgrade, and without a workspace odctl's images run with odctl's own version instead of a cached `latest`.

1.0.0: documentation site and compatibility promise

A documentation site with guides, profile pages and the CLI reference. Semantic versioning with a compatibility promise for 1.x. `odctl up` works straight after `odctl recreate`.

What each release changed is in the [Changelog](https://jaehyeon.me/odctl/latest/about/changelog/index.md) and on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).
