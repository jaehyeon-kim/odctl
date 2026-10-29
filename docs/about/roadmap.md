# Roadmap

The work comes in the order shown, without dates: a release ships when it is ready. Features come first, then the testing and setup work that adds no feature. Each planned item links to its GitHub issue where one exists.

## Next Releases

::timeline::
- title: '1.4.0: Feast'
  content: 'An MCP endpoint for agents, pushing streaming features and materialising from Airflow, and vector retrieval on PostgreSQL. [#150](https://github.com/jaehyeon-kim/odctl/issues/150)'
  icon: ':material-play:'
  key: now
- title: '1.5.0: Stable interface and JSON output'
  content: 'A written list of what 1.x keeps stable: profile names, ports, `.env` keys, volumes and the workspace files. `--json` on `list`, `explain`, `ps` and `info`, and `--yes` on `init` and `down` for scripts. [#140](https://github.com/jaehyeon-kim/odctl/issues/140)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.6.0: MCP server'
  content: 'Tools for AI agents that show the profiles and what is running, with `up` and `down` behind a setting. [#141](https://github.com/jaehyeon-kim/odctl/issues/141)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.7.0: Langfuse'
  content: 'A profile for tracing and evaluating LLM and agent applications, using odctl''s ClickHouse. [#120](https://github.com/jaehyeon-kim/odctl/issues/120)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.8.0: Snapshot and restore'
  content: '`odctl snapshot` and `odctl restore` save a profile''s data and bring it back, so a lab or an agent can start again from a known state. [#142](https://github.com/jaehyeon-kim/odctl/issues/142)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.9.0: Lineage and alerts'
  content: 'Lineage from Airflow, Spark and Feast in Marquez, and Grafana alert rules, starting with one for a failed DAG run. [#149](https://github.com/jaehyeon-kim/odctl/issues/149)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.10.0: Kafka Connect transforms'
  content: 'Transforms built into the Connect image: make a record schema required, replace personal fields with a hash, and send lineage events to Marquez for any connector. [#143](https://github.com/jaehyeon-kim/odctl/issues/143)'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.11.0: Memory check and models on the host'
  content: '`odctl up` warns when Docker has less memory than the profiles it starts need. One setting lets containers reach a model server on the host with an OpenAI-compatible API, such as Ollama or LM Studio, on macOS, Linux and WSL2. The guide also covers the Ollama embeddings route, batch embedding in Airflow and a hand-run rerank server. [#155](https://github.com/jaehyeon-kim/odctl/issues/155), [#109](https://github.com/jaehyeon-kim/odctl/issues/109)'
  icon: ':material-clock-outline:'
  key: planned
- title: 'MLOps guides'
  content: 'Guides for a prediction log and labels in PostgreSQL, feature and leakage checks, hyperparameter search, ONNX quantisation, serving a second model or many models, serving latency sent over OTLP, Feast dataset versions and reads of large Iceberg tables. No new service and no new version: the guides are published when they reach `main`.'
  icon: ':material-clock-outline:'
  key: planned
- title: 'Agents guides'
  content: 'Guides for traces, token metrics, feedback and evaluation of agent and model calls, an agent in a Temporal workflow, agent services beside the stack, and agent state in PostgreSQL. No new service and no new version.'
  icon: ':material-clock-outline:'
  key: planned
- title: 'Retrieval guides'
  content: 'Guides for hybrid search with rank fusion, graph queries in PostgreSQL, ingestion with change detection, Valkey as a cache, and media with signed URLs. No new service and no new version.'
  icon: ':material-clock-outline:'
  key: planned
- title: '1.12.0: Label Studio'
  content: 'A `label-studio` profile for labelling data by hand, on odctl''s PostgreSQL. Its guide loads the exported labels into the label table of the MLOps guides.'
  icon: ':material-clock-outline:'
  key: planned
::/timeline::

## Alongside

Work that does not wait for a release, published as it is ready.

<div class="grid cards" markdown>

-   __Guides__

    ---

    Iceberg table maintenance with Spark, vector search in Valkey, and traces and prompts in MLflow.

    [#152](https://github.com/jaehyeon-kim/odctl/issues/152)

-   __Testing and CI__

    ---

    It lands between 1.10.0 and 1.11.0. It changes only the tests, the CI workflows, the dependency update settings and two docs pages, not odctl itself, so it has no version of its own. The end-to-end tests run on every pull request, including image updates, so an update is tested before it merges. Each release is also tested as an upgrade from the one before it, and on arm64, which most Macs run. A pull request then tests only the profiles it changes, and the full suite runs every night. The CI user guide and the per-task environments section are published with 1.11.0.

    [#102](https://github.com/jaehyeon-kim/odctl/issues/102)

</div>

## After desflow 1.0

<div class="grid cards" markdown>

-   __desflow server__

    ---

    When the desflow server ships: a profile that runs the [desflow](https://jaehyeon.me/desflow/) simulation server, so a project can start simulations that write to Kafka, PostgreSQL or Iceberg.

    [#144](https://github.com/jaehyeon-kim/odctl/issues/144)

</div>

## Released

Newest first.

??? note "1.3.0: OpenMetadata connectors"

    Custom OpenMetadata connectors uploaded to S3 are picked up by the ingestion container with no restart, AutoPilot is off by default, extra packages can be installed in the ingestion container, and OpenMetadata runs 2.0.7.

??? note "1.2.2: newer images"

    Trino, Metabase, `otel-lgtm` and the PostgreSQL JDBC driver in the deps image are updated, and the Grafana dashboard descriptions no longer name the exact version of the component they show.

??? note "1.2.1: recreate on several files"

    `odctl recreate`, `odctl restart` and `odctl logs` work on profiles from more than one compose file, `odctl init` and `odctl down` can skip their prompt, and the docs show every command with a runnable example.

??? note "1.2.0: Streaming"

    Flink writes to HTTP APIs such as Feast's push endpoint, Spark reads Kafka without downloading packages, and new guides cover Kafka retention and several rolling windows in Flink SQL. The release also fixes the MLflow and storage guides and sets `GOMEMLIMIT`, a soft limit for the Go runtime, on `seaweed`, so large model uploads do not hit its container memory limit.

??? note "1.1.0: localhost-only services"

    Every service is reachable from your machine only, Kafka no longer publishes the minikube listener ports, an odctl skill and `llms.txt` help AI assistants, and the docs have this Roadmap and a [Changelog](changelog.md).

??? note "1.0.2: Python 3.15"

    odctl is tested on Python 3.15, ZooKeeper and Metabase are updated, and Renovate groups image updates by compose file.

??? note "1.0.1: upgrade fixes"

    Old jars no longer stay in the shared deps volume after an upgrade, and without a workspace odctl's images run with odctl's own version instead of a cached `latest`.

??? note "1.0.0: documentation site and compatibility promise"

    A documentation site with guides, profile pages and the CLI reference. Semantic versioning with a compatibility promise for 1.x. `odctl up` works straight after `odctl recreate`.

What each release changed is in the [Changelog](changelog.md) and on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).
