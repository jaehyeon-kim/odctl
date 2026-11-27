# Roadmap

Now is the work being built, and Planned lists the rest in no order. Neither has dates or version numbers: an item gets its version when it ships. Each item links to its GitHub issue where one exists.

## Now

Nothing is being built now. The next item comes from Planned.

## Planned

- **Guides**

  ______________________________________________________________________

  Iceberg table maintenance with Spark, vector search in Valkey, and traces and prompts in MLflow.

  [#152](https://github.com/jaehyeon-kim/odctl/issues/152)

- **MLOps guides**

  ______________________________________________________________________

  A prediction log and labels in PostgreSQL, feature and leakage checks, hyperparameter search, ONNX quantisation, serving a second model or many models, serving latency sent over OTLP, Feast dataset versions and reads of large Iceberg tables.

- **Agents guides**

  ______________________________________________________________________

  Traces, token metrics, feedback and evaluation of agent and model calls, an agent in a Temporal workflow, agent services beside the stack, and agent state in PostgreSQL.

- **Retrieval guides**

  ______________________________________________________________________

  Hybrid search with rank fusion, graph queries in PostgreSQL, ingestion with change detection, Valkey as a cache, and media with signed URLs.

- **Testing and CI**

  ______________________________________________________________________

  The end-to-end tests run on every pull request, including image updates. Each release is also tested as an upgrade from the one before it, and on arm64.

  [#102](https://github.com/jaehyeon-kim/odctl/issues/102)

- **Kafka Connect transforms**

  ______________________________________________________________________

  Transforms built into the Connect image: make a record schema required, replace personal fields with a hash, and send lineage events to Marquez for any connector.

  [#143](https://github.com/jaehyeon-kim/odctl/issues/143)

- **desflow server**

  ______________________________________________________________________

  When the desflow server ships: a profile that runs the [desflow](https://jaehyeon.me/desflow/) simulation server, so a project can start simulations that write to Kafka, PostgreSQL or Iceberg.

  [#144](https://github.com/jaehyeon-kim/odctl/issues/144)

## Released

Newest first.

1.10.0: Agent skill and plugin

The odctl agent skill is rewritten around the container lifecycle, with a checklist, rules that each show a wrong and a right example, and reference pages, and a plugin installs it with the read-only MCP server in Claude Code, Codex and Antigravity ([AI Assistants](https://jaehyeon.me/odctl/latest/ai/index.md)). [#177](https://github.com/jaehyeon-kim/odctl/issues/177)

A workspace compose file that cannot be read stops each command with an error that says why, `odctl explain` names the role of the Langfuse server and worker, Feast's feature server and Label Studio, and the Trino notes give a `docker exec` command that works without a terminal.

1.9.0: Label Studio

The `label-studio` profile runs Label Studio on odctl's PostgreSQL, and its guide loads the exported labels into a label table in PostgreSQL, which the MLOps guides then use ([Label Studio](https://jaehyeon.me/odctl/latest/guides/label-studio/index.md)). MLflow is 3.18.0 and Feast is 0.68.0. [#169](https://github.com/jaehyeon-kim/odctl/issues/169), [#184](https://github.com/jaehyeon-kim/odctl/issues/184)

1.8.0: Lineage and alerts

Airflow, Spark and Feast send their lineage to Marquez ([OpenLineage and Marquez](https://jaehyeon.me/odctl/latest/guides/lineage/index.md)), and the Airflow image has Feast's `openlineage` extra. The `telemetry` profile loads Grafana alert rules from the workspace and ships one for a failed DAG run, and the Telemetry guide adds sample rules for data drift and a token budget ([Add an Alert Rule](https://jaehyeon.me/odctl/latest/guides/telemetry/#add-an-alert-rule)). [#149](https://github.com/jaehyeon-kim/odctl/issues/149)

1.7.0: Langfuse

The `langfuse` profile traces LLM and agent applications in Langfuse, on odctl's PostgreSQL, ClickHouse, Valkey and SeaweedFS ([Langfuse](https://jaehyeon.me/odctl/latest/guides/langfuse/index.md)). On a new database, `admin@odctl.io` logs in to OpenMetadata with the password `password` ([OpenMetadata](https://jaehyeon.me/odctl/latest/guides/openmetadata/index.md)). [#120](https://github.com/jaehyeon-kim/odctl/issues/120), [#181](https://github.com/jaehyeon-kim/odctl/issues/181)

1.6.0: MCP server

`odctl mcp` gives an AI agent `list`, `explain`, `ps`, `info` and `logs` as MCP tools, and `up` and `down` with `--allow-changes` ([MCP Server](https://jaehyeon.me/odctl/latest/guides/mcp-server/index.md)). The dry run of `odctl down --volumes` names the volumes it would remove. [#141](https://github.com/jaehyeon-kim/odctl/issues/141), [#170](https://github.com/jaehyeon-kim/odctl/issues/170)

1.5.0: JSON output and what stays stable in 1.x

`odctl list`, `explain`, `ps` and `info` print JSON with `--json`, and [What Stays Stable in 1.x](https://jaehyeon.me/odctl/latest/how-it-works/#what-stays-stable-in-1x) lists what every 1.x release keeps. [#140](https://github.com/jaehyeon-kim/odctl/issues/140)

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
