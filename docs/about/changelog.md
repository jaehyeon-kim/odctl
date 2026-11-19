# Changelog

Each release, newest first: what changed, then under Upgrading what to change in commands, workspaces or clients that use the previous release. Releases up to 1.0.2 are described on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).

## Version 1.10.0

A plugin that installs the odctl skill and the MCP server in Claude Code, Codex and Antigravity, a rewritten skill, clearer errors, and fixes from a review of the CLI.

- A plugin installs the odctl skill and the read-only MCP server in Claude Code, Codex and Antigravity ([Plugin](../ai/plugin.md)). Install odctl with `uv tool install 'odctl[mcp]'` first, then:
    - Claude Code: `claude plugin marketplace add jaehyeon-kim/odctl`, then `claude plugin install odctl@odctl`.
    - Codex: `codex plugin marketplace add jaehyeon-kim/odctl`, then `codex plugin add odctl@odctl`.
    - Antigravity: `agy plugin install https://github.com/jaehyeon-kim/odctl`.
- The docs have an AI Assistants section for the plugin, the skill, the MCP server and `llms.txt` ([AI Assistants](../ai/index.md)). The MCP Server guide keeps its address.
- The agent skill is rewritten around the container lifecycle: a checklist, rules that each show a wrong and a right example, and reference pages for each profile's addresses and logins and for odctl in a project's tests ([Agent Skill](../ai/agent-skill.md), [Use It with an AI Assistant](../getting-started.md#use-it-with-an-ai-assistant)).
- OpenMetadata is 2.0.8, Confluent's converters are 8.4.1 and Debezium is 3.7.1.
- The Trino notes of `odctl explain trino` give `docker exec trino trino --execute '<query>'`, which works without a terminal ([Trino and Metabase](../guides/trino-metabase.md)).
- A compose file in your workspace that is missing, is not UTF-8 text or is not valid YAML now stops every command that reads it with `Cannot read <file>: ...`, which says which of these it is. A dry run of `up` or `down` without `--volumes` still prints the plan. Before, `down --volumes --dry-run` ended in a traceback, `info --json` left that file's images out, and the tables listed `File Error` as that file's services.
- A volume such as `${PG_VOLUME:-pgdata}:/var/lib/postgresql/data`, in the short or the long form, is expanded before it is read, and a volume without `name:` is named after the project Compose runs, so `down --volumes --dry-run` lists the volume the real run removes. A source starting with `~` counts as a folder on the host, as Compose reads it.
- A service with no `profiles:` key, which Compose starts with every profile of its file, is now listed by `ps`, `explain`, `logs --service` and `down`.
- odctl passes each compose file's project name to Compose, so a `COMPOSE_PROJECT_NAME` in the shell or in `.env` no longer puts every file into one project, where `odctl down kafka-lite` removed the containers of the other profiles. A container counts for a file only when both its project and its service are that file's, so `ps`, `down` and the idle check of the shared jar volume no longer mix two files' services of the same name.
- `odctl up` no longer reads a missing credential helper, or any other registry error whose text holds `not found`, as an image that is not published.
- The check that warns about an old TAG in the workspace `.env` reads the file as Compose reads it, so `export TAG=1.9.0` and `TAG = 1.9.0` give the same answer as the image tag odctl runs.
- A workspace whose `.env` has an empty TAG, or no TAG line, now runs the images of the CLI's version. Before, Compose ran the `latest` images.
- `odctl init` and `odctl init --force` refuse a folder that holds files and no `registry.yml`, and a path that is a file. Its question names the folder it removes. `odctl init` copies `registry.yml` first, so an `init` that fails part way can be run again.
- A `registry.yml` that is missing, empty, not UTF-8 text, not valid YAML or not in the registry's form now stops each command with `Cannot read <path>: ...`. Before, `explain` and the dry runs of `up` and `down` ended in a traceback.
- A registry whose profile is listed under two stacks or twice in one stack, whose stack lists dependencies for a profile of another stack, or whose dependency names no profile, now stops with a message that names the profile.
- `odctl up` starts the file of a dependency before the file of the profile that depends on it, read from `depends_on` in the registry. Before, a workspace profile could start before a dependency in another file.
- A failed pull in `odctl up --pull` prints `Failed to pull images for <file>` and exits 1. Before, it ended in a traceback.
- `restart`, `recreate` and `logs` print `Failed to <verb> <file>` with Docker's message when a Compose call fails, and `restart` and `recreate` print each file before they act on it. Before, they ended in a traceback.
- `odctl recreate deps` no longer waits on the container that copies the jars and exits. `odctl up` and `odctl recreate` stop with `Failed to <verb> compose-deps.yml` when that container exits with a code other than 0. Before, they went on as if the jars had been copied.
- A followed log stream that fails, as in `odctl logs kafka-lite -f`, prints `Failed to fetch logs for <file>` and exits 1 as soon as it fails, while other streams still follow, and also when Ctrl+C comes after the failure. Before, it printed a thread traceback and exited 0.
- `odctl logs <profile> --service <name>` with a service that none of the profiles defines prints an error that names the service and the profiles, and exits 1. Before, it printed nothing and exited 0.
- The MCP tool `down` with `volumes` set refuses a call that names every profile except `deps`, because that call removes all data, which only `odctl down --all --volumes` in a terminal does after asking. A tool call that reaches a question of the command returns the command's text as its error, where before it returned only `Error executing tool down`.
- `odctl down <every profile> --volumes` asks the same question as `odctl down --all --volumes`, unless `--yes` is given.
- `odctl down deps --volumes` keeps the shared jar volume while other profiles still have containers that use it, and says so, as the help of `--volumes` describes. Its dry run without Docker shows that deps is stopped in every case and that only the volume depends on the other profiles. The dry run of `down <profile> --volumes` also lists, under `compose-deps.yml`, the unnamed volumes of the stopped containers, if any.
- A registry description, role, file or profile name, a compose service, port or volume name, or an error from Docker, that holds square brackets is printed as written, in `list`, `explain`, the dry runs and the progress lines. Before, `list` and `explain` could end in a markup error, and text such as `[bold]` disappeared.
- The Network Mapping of `odctl explain` prints the ports with variables expanded, as `explain --json` does, leaves out a port with no host part or a port range, and adds the protocol only when it is not tcp. Before, `${KAFKA_PORT:-19092}` printed as `Host -19092}`.
- `odctl explain` lists a service built from source, with no image, as `built locally`. Before, it was left out when another service had an image.
- `odctl ps` counts a profile as active only when its services are running, or, for a one-shot service that another service waits on, have exited with code 0. Before, a stopped container counted as running.
- `odctl explain` names the role of the Langfuse server and worker, Feast's feature server, ZooKeeper, the ClickHouse shard 2 stand-in and Label Studio. Each role matches the image's repository rather than any text in the image name, with or without a tag or a digest.
- The skill's description names Label Studio and Metabase, so an assistant loads it for a task that needs them.
- odctl reads the workspace `.env` as Compose does: it drops a UTF-8 byte order mark, strips an inline comment after a space, removes quotes, applies escapes inside double quotes and expands `${OTHER}`, and `${OTHER}` in a value reads a variable set in the shell before one set earlier in the file. Before, `TAG=1.9.0 # pinned` made odctl check the registry for the tag `1.9.0 # pinned`.
- `odctl down <profile> --volumes` for a profile your workspace adds to `compose-deps.yml`, such as `deps-extra`, now removes that profile's own volumes, as `docker compose down --volumes` does. Before, they stayed while any other profile had a container. A profile that mounts the shared jar volume still keeps it until no other profile has a container. The dry run lists the same volumes, with `--all` too.
- odctl reads your compose files as Docker Compose reads them. A port written without quotes, such as `2222:22`, now shows in `list -d`, `explain` and `ps`, where it used to be read as a number and left out. `yes`, `on` and `off` stay text. A key tagged `!reset` under a `<<` merge key now takes the merged value, as Compose does.
- A workspace profile name with square brackets no longer stops `odctl up --pull` or `odctl ps` with a markup error.
- `odctl --help` no longer prints the internal `Args:` notes of the `info` command.

### Upgrading

- When a compose file in your workspace is missing, is not UTF-8 text or is not valid YAML, odctl now stops with exit code 1 and `Cannot read <file>: ...`, which says which of these it is. Before 1.10.0, the commands without `--json` listed `File Error` or `Err: <type>` as that file's service, port, image and volume, `info --json` left that file's images out, and `down --volumes --dry-run` ended in a traceback. A dry run of `up` or `down` without `--volumes` still prints the plan. Fix the file, or run `odctl init --force` to copy the packaged one; it replaces your edits, so keep a copy of them.
- `odctl explain` names the role of the Langfuse server and worker, Feast's feature server, ZooKeeper, the ClickHouse shard 2 stand-in and Label Studio, which it showed as `Service Container`. A script that reads that line sees the new role. A workspace whose compose file uses the image `valkey/valkey`, which only 0.0.1 and 0.0.2 shipped, now shows `Service Container` for it; the packaged `valkey/valkey-bundle` keeps its role.
- The Trino notes that `odctl explain trino` prints now give `docker exec trino trino --execute '<query>'`, which works without a terminal. A workspace made by `odctl init` before 1.10.0 keeps its old `registry.yml`, so run `odctl init --force` to copy the new text; it replaces your edits, so keep a copy of them.
- OpenMetadata is 2.0.8, up from 2.0.7. A workspace made by `odctl init` before 1.10.0 keeps its old `compose-metadata.yml`, which runs 2.0.7: run `odctl init --force` to copy the new file; it replaces your edits, so keep a copy of them. On the next `odctl up` with the metadata profile, `openmetadata-migrate` applies 2.0.8's database migrations to an existing OpenMetadata database.
- A workspace service with no `profiles:` now appears in the `services` of `list --json`, `explain --json` and `ps --json`, and `down` stops it with its profile.
- odctl now ignores `COMPOSE_PROJECT_NAME`. Each compose file runs as the project its `name:` names. If you changed `name:` in a workspace file, odctl now manages the containers of that project. If you set `COMPOSE_PROJECT_NAME` for an earlier version, its containers stay in that project, which odctl no longer manages, and `odctl up` fails while their fixed container names are in use. Remove them with `docker compose -p <that name> down` before you run `odctl up`.
- A workspace whose `.env` has an empty TAG, or no TAG line, now runs the images of the CLI's version, not `latest`. Set TAG in `.env` to run another version.
- `odctl init` and `odctl init --force` now refuse a `--workspace` that names a file, or a folder that holds files and no `registry.yml`. Name a new or empty folder, or an existing workspace.
- A workspace registry with a profile listed under two stacks or twice in one stack, a `depends_on` key that is a profile of another stack, or a dependency that no stack lists, loaded before and now stops every command with a message. Fix the entry it names.
- `odctl up` and `odctl recreate` now exit 1 when the container that copies the jars into `odctl-shared-deps` exits with a code other than 0, where they went on and exited 0.
- A failed `odctl logs -f` now exits 1, where it exited 0.
- `odctl logs <profile> --service <name>` with a service that none of the profiles defines now exits 1, where it printed nothing and exited 0.
- The MCP tool `down` now refuses a call with `volumes` set that names every profile except `deps`, which it accepted. To remove every profile's data, run `odctl down --all --volumes` in a terminal, which asks first, or name fewer profiles.
- A script that runs `odctl down` with every profile and `--volumes` now needs `--yes`, because the command asks first.
- `odctl down deps --volumes` now keeps the shared jar volume `odctl-shared-deps` while other profiles have containers. Stop them first, or run `odctl down --all --volumes`, to remove it.
- `active_profiles` in `odctl ps --json` no longer lists a profile whose containers are stopped. A one-shot container that exited with code 0 still counts.
- odctl now reads `.env` as Compose does. A value with an inline comment, quotes, escapes or `${OTHER}`, such as `TAG=1.9.0 # pinned`, now gives the value Compose uses, and `${OTHER}` in a value reads a variable set in the shell before one set earlier in the file, so `odctl info` and the check for a published image can show a different tag than before.

## Version 1.9.0

Label Studio, and MLflow 3.18.0 and Feast 0.68.0.

- The `label-studio` profile runs Label Studio on odctl's PostgreSQL, and its guide loads the exported labels into a label table in PostgreSQL ([Label Studio](../guides/label-studio.md)).
- Label Studio can reach an ML backend, a webhook receiver and SeaweedFS on the `odctl` network, and the `storage` profile creates a `label-studio` bucket for its S3 storage ([Connect Other Services](../guides/label-studio.md#connect-other-services)).
- MLflow is 3.18.0. On each start, `mlflow` upgrades the schema of a database that an earlier MLflow created.
- A download of a model from the host works with no client setting ([Load a Model from Your Machine](../guides/mlflow.md#load-a-model-from-your-machine)).
- MLflow's automatic evaluation scores traces with a judge that uses an AI Gateway endpoint. Before, every assessment failed with "Invalid Host header" ([MLflow](../guides/mlflow.md)).
- Feast is 0.68.0.
- `feast-serve` and `feast-ui` keep running when `s3://feast/repo` changes while they load it. Before, a file deleted during the load stopped the container until the next `odctl up`.
- The docs site lists one version per minor release, such as 1.2, with the docs of its last patch. Patch versions are no longer listed, so an address with one, such as `https://jaehyeon.me/odctl/1.2.0/`, now returns 404; use the minor, `https://jaehyeon.me/odctl/1.2/`.

### Upgrading

- A new profile, `label-studio`, in the `mlops` stack. It starts PostgreSQL and uses host port 8088.
- A workspace made by `odctl init` before 1.9.0 has an older `compose-mlops.yml`, `compose-infra.yml` and PostgreSQL init script. Run `odctl init --force` to copy the new files; it replaces your edits, including `.env`, so keep a copy of them. Put your settings back into the new `.env` before you start the services, because a `postgres` container keeps the user and password it was created with. A `postgres` container started before 1.9.0 does not run the init script again, so it has no `labelstudio` database. Start it with `odctl up postgres`, then create the database once before `odctl up label-studio`: `docker exec postgres psql -U user -d postgres -c 'CREATE DATABASE labelstudio OWNER "user"'`. The `postgres` database always exists, whatever `POSTGRES_DB` is set to. If you set `POSTGRES_USER`, put that name in place of `user` in both places.
- MLflow is 3.18.0, up from 3.16.1. On its next start, `mlflow` upgrades the schema of your existing `mlflow` database. Going back to 3.16.1 afterwards is not tested. Install `mlflow==3.18.0` on the host to match the server.
- A download from the host no longer needs `MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false`; you can remove it.
- Feast is 0.68.0, up from 0.66.0, and needs Python 3.11 or newer. Install `feast[...]==0.68.0` on the host. The feature server's latency metric labels `feature_count` with a range, such as `1-10`, so a query that matches a single count changes.

## Version 1.8.0

Lineage from Airflow, Spark and Feast in Marquez, and Grafana alert rules in the `telemetry` profile.

- Airflow sends each DAG run's lineage to Marquez when `AIRFLOW_OPENLINEAGE_TRANSPORT` is set in `.env`; the key is empty by default ([Lineage from Airflow](../guides/lineage.md#lineage-from-airflow)).
- A Spark job sends its lineage to Marquez through the OpenLineage Spark listener, whose jar the Spark containers already load ([Lineage from Spark](../guides/lineage.md#lineage-from-spark)).
- `feast apply` sends the feature views it applies to Marquez when `feature_store.yaml` enables it, and the `airflow` image has Feast's `openlineage` extra for that ([Lineage from Feast](../guides/lineage.md#lineage-from-feast)).
- The `telemetry` profile loads Grafana alert rules from `.odctl/grafana/alerting/` and ships one that fires when an Airflow DAG run fails ([Add an Alert Rule](../guides/telemetry.md#add-an-alert-rule)).
- The Telemetry guide has two sample rules: one for data drift found by an Evidently check in an Airflow DAG, and one for a budget of model tokens.

### Upgrading

- A new `.env` key, `AIRFLOW_OPENLINEAGE_TRANSPORT`, is empty by default, so nothing changes until you set it.
- A workspace made by `odctl init` before 1.8.0 keeps its old `compose-orch.yml` and `compose-obsv.yml`, has no `grafana/alerting` folder, and has no `AIRFLOW_OPENLINEAGE_TRANSPORT` line in its `.env`. Run `odctl init --force` to copy the new files and write a new `.env` that has the key; it replaces your edits, so keep a copy of them. Then set the key as [Lineage from Airflow](../guides/lineage.md#lineage-from-airflow) shows, and run `odctl recreate` for the profiles you use, such as `odctl recreate airflow telemetry`.

## Version 1.7.0

A Langfuse profile for tracing LLM and agent applications, Valkey starting earlier, the OpenMetadata admin's password changed to `password`, and newer otel-lgtm and Confluent converters.

- The `langfuse` profile runs Langfuse in a new AI Engineering area, with its UI and OTLP endpoint on host port 3005 ([Langfuse](../guides/langfuse.md)).
- The `storage` profile also creates a `langfuse` bucket.
- `valkey` now starts before the other profiles that sort after it, so `odctl up` and its `--dry-run` list it earlier ([Dependencies and the Start Order](../how-it-works.md#dependencies-and-the-start-order)).
- On a new database, `admin@odctl.io` logs in to OpenMetadata with the password `password`, the same as `user@odctl.io` ([OpenMetadata](../guides/openmetadata.md)).
- The `telemetry` profile runs `grafana/otel-lgtm:0.40.0`, up from 0.37.0. The deps image has the Confluent Avro, Protobuf and JSON Schema converters 8.4.0, up from 8.3.2.

### Upgrading

- A workspace made by `odctl init` before 1.7.0 keeps its old files: it has no `langfuse` profile, `telemetry` keeps `otel-lgtm` 0.37.0, and a new OpenMetadata database gives `admin@odctl.io` the password `admin`. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate` for the profiles you use, such as `odctl recreate telemetry metadata`.
- A `ch-lite` with data from an earlier release does not run its init file again, so it has no `langfuse` database. Start it with `odctl up ch-lite` and create the database: `docker exec ch-11 clickhouse-client --password password --query "CREATE DATABASE IF NOT EXISTS langfuse"`. Then run `odctl up langfuse`: `seaweed-init` creates the `langfuse` bucket, and Langfuse creates its PostgreSQL database.
- An OpenMetadata database created by 1.3.0 to 1.6.0 keeps the admin password `admin`, so a script that logs in as `admin@odctl.io` uses `admin` there and `password` on a new database. `openmetadata-init` accepts both.

## Version 1.6.0

An MCP server that gives AI agents odctl's profiles, containers and logs, and a dry run of `odctl down --volumes` that names the volumes.

- `odctl mcp` serves `list`, `explain`, `ps`, `info` and `logs` as tools to an MCP client, such as Claude Code, after `uv tool install "odctl[mcp]"` ([MCP Server](../guides/mcp-server.md)).
- All tools but `logs` return the same JSON as `--json`, and their names and parameter names stay the same in every 1.x release ([What Stays Stable in 1.x](../how-it-works.md#what-stays-stable-in-1x)).
- `odctl mcp --allow-changes` also serves `up` and `down`, so an agent can start and stop profiles.
- The `down` tool with `volumes` refuses profiles that cover all that `odctl down --all --volumes` would remove, because that command asks first and the server cannot ask.
- `odctl down --volumes --dry-run` names the volumes the real run would remove: the named volumes, the number of unnamed volumes of each container, and `odctl-shared-deps` once no other profile has a container.
- `odctl down --all --dry-run` reports that Docker is not reachable instead of ending with a traceback.
- odctl reads Compose variables in a workspace file in every form Compose supports, such as `$VAR`, `${VAR:+word}` and a nested default, so the images, ports and volume names it shows match what Compose runs.

## Version 1.5.0

JSON output from `list`, `explain`, `ps` and `info`, a written list of what 1.x keeps stable, and newer SeaweedFS, Valkey and Spark images.

- `odctl list`, `odctl explain`, `odctl ps` and `odctl info` take `--json` and print one JSON document for scripts and AI assistants, with warnings and errors on stderr ([JSON Output](../json-output.md), [Getting Started](../getting-started.md)).
- `odctl explain` names a dependency the registry lists but no stack defines, instead of ending with a traceback; it still exits 1.
- `odctl info --json` also shows the image tag, the workspace and which of odctl's own images are on your machine.
- [What Stays Stable in 1.x](../how-it-works.md#what-stays-stable-in-1x) lists what every 1.x release keeps: profile names, published ports, `.env` keys, volumes, the workspace files and the `--json` keys.
- odctl now needs Typer 0.18.0 or later, because older Typer releases misread odctl's options with newer Click releases; with some pairs `odctl init` replaced an existing workspace without asking.
- The base of odctl's `postgres` image, `postgres:18-trixie`, is pinned by digest, so a release that does not change the image no longer gives it new layers to download.
- SeaweedFS runs `chrislusf/seaweedfs:4.52`, up from 4.48. Valkey runs `valkey/valkey-bundle:9.1.4-alpine`, up from 9.1.3. odctl's Spark image is built on `apache/spark:4.1.4`, up from 4.1.3, and the deps image has the Spark Kafka connector 4.1.4.
- The odctl skill (`skills/odctl/SKILL.md`) names each image without its tag; `odctl explain <profile>` shows the tag.

### Upgrading

- A workspace made by `odctl init` with an earlier release keeps its old `compose-infra.yml` and `compose-store.yml`, and so the old SeaweedFS and Valkey images. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate` for the profiles you use, such as `odctl recreate storage valkey`.

## Version 1.4.0

Feast's MCP endpoint, pushing features over HTTP and from Flink, materialising from Airflow, and vector retrieval on PostgreSQL.

- `feast-serve` serves an MCP endpoint at `http://127.0.0.1:6566/mcp` with each route of the feature server as a tool ([Connect an MCP Client](../guides/feast-iceberg.md#connect-an-mcp-client)).
- [Push Features](../guides/feast-iceberg.md#push-features) pushes a value to the feature server [Over HTTP](../guides/feast-iceberg.md#over-http) and [From Flink SQL](../guides/feast-iceberg.md#from-flink-sql), then reads it back.
- [On a Schedule](../guides/feast-iceberg.md#on-a-schedule) materialises the feature view into Valkey from an Airflow DAG every hour.
- [Vector Retrieval with Feast](../guides/feast-vector-retrieval.md) writes document embeddings to PostgreSQL with pgvector and retrieves the nearest rows.
- `feast apply` in the Feast guide now runs with `--skip-source-validation`, so the same definitions work from your shell and from the Airflow container.

### Upgrading

- A workspace made by `odctl init` before 1.4.0 keeps its `feast/feature_store.yaml` without the MCP endpoint, and its `registry.yml` without the MCP line in `odctl explain feast`. Run `odctl init --force` to copy the new files (it replaces your edits), or add the `feature_server` block yourself. Then run `odctl recreate feast`.
- If you applied the guide's definitions before 1.4.0, their Iceberg source stores `endpoint`, the catalog address of your shell, which the Airflow container cannot reach. Remove `endpoint` from the source and run `feast apply --skip-source-validation` again before you run the DAG.

## Version 1.3.0

Custom connectors for OpenMetadata, extra packages for its ingestion container, AutoPilot off by default, OpenMetadata 2.0.7, and newer Kafka and Metabase images.

- A Python connector uploaded to `s3://openmetadata/connectors` is importable in the ingestion container within about 15 seconds, and a change to it is used by the next agent run with no restart. [Add a Custom Connector](../guides/openmetadata.md#add-a-custom-connector) creates its service and agent through the API.
- OpenMetadata's AutoPilot, which creates and runs default agents for a service added in the UI, is off by default. The new `.env` key `METADATA_AUTOPILOT` turns it on, and the new `openmetadata-init` service applies it each time `metadata` starts. See [Register PostgreSQL as a Database Service](../guides/openmetadata.md#register-postgresql-as-a-database-service).
- `_METADATA_PIP_DEPS` in `.odctl/.env` installs extra Python packages in the `openmetadata-ingestion` container, as `_AIRFLOW_PIP_DEPS` does for Airflow. See [Examples](../how-it-works.md#examples).
- `openmetadata-ingestion` has a healthcheck, so `odctl up` and `odctl recreate` return once its Airflow answers.
- [Where Data Lives](../how-it-works.md#where-data-lives) shows the three profiles that read their code from a bucket: `airflow`, `feast` and `metadata`.
- OpenMetadata and its ingestion container run 2.0.7, up from 2.0.1.
- On a new database the sign-in domain is `odctl.io`, and a second admin `user@odctl.io` has the password `password`. The ingestion Airflow takes `user` and `password`.
- Kafka and Kafka Connect run `apache/kafka:4.3.2`, up from 4.3.1. Metabase runs v0.64.3.5, up from v0.64.3.1. The deps image has `log4j-slf4j2-impl` 2.26.1, up from 2.23.1.

### Upgrading

- The `metadata` profile now also starts `storage`, SeaweedFS on 127.0.0.1 ports 8333, 8889 and 9333, from which the ingestion container takes connectors.
- Two new `.env` keys, `_METADATA_PIP_DEPS` and `METADATA_AUTOPILOT`, are written by `odctl init`. An existing `.env` works without them: add the lines, or get them with `odctl init --force`.
- AutoPilot is now off unless `METADATA_AUTOPILOT="true"`, so a service added in the OpenMetadata UI no longer gets default agents. An existing `.env` has no key, which means off. Set `METADATA_AUTOPILOT="true"` in `.odctl/.env` to keep the old behaviour.
- `openmetadata-migrate` runs `openmetadata-ops.sh migrate` against your existing database on the next start of `metadata`, by `odctl up` or `odctl recreate`, for the move from 2.0.1 to 2.0.7. Going back to 2.0.1 afterwards is not tested.
- The sign-in domain `odctl.io` and the password `password` of `user` apply to a new database only. A database from an earlier release keeps its users `admin@open-data.local` and `user@open-data.local`, both with the password `admin`, because the server restores a user's stored email on every update (`UserRepository.java`, `entitySpecificUpdate`, at `2.0.7-release`) and keeps a stored password. On that database `admin@odctl.io` and `user@odctl.io` fail with HTTP 400, "You have entered an invalid username or password."
- The ingestion Airflow login changes from `admin` / `admin` to `user` / `password`.
- A workspace made by `odctl init` with an earlier release keeps its old `compose-metadata.yml`, `compose-infra.yml`, `compose-kafka.yml`, `compose-analytics.yml` and `registry.yml`, has no `openmetadata/connector_sync.py` or `openmetadata/autopilot_init.py`, and so has none of the changes above. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate metadata storage`, and `odctl recreate` for the Kafka and Metabase profiles you use, such as `odctl recreate kafka-lite metabase`.

## Version 1.2.2

Newer images for Trino, Metabase and the observability stack.

- Trino runs 484, up from 483. Metabase runs v0.64.3.1, up from v0.63.19.3. `otel-lgtm` runs `grafana/otel-lgtm:0.37.0`, up from 0.35.0. The deps image has the PostgreSQL JDBC driver 42.7.14, up from 42.7.13.
- The Grafana dashboard descriptions no longer name the exact version of the component they show, so they stay true when an image is updated. They name a major version only where it tells two kinds apart: Flink 2, whose metrics differ from Flink 1, and OpenMetadata 2, which is maintained beside OpenMetadata 1.

### Upgrading

- A workspace made by `odctl init` with an earlier release keeps its old compose files, and so the old images. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate` for the profiles you use, such as `odctl recreate trino metabase`.

## Version 1.2.1

`recreate`, `restart` and `logs` work on profiles from several compose files, `init` and `down` can skip their prompt, and the docs show every command with a runnable example.

- `odctl recreate`, `odctl restart` and `odctl logs` work on profiles from more than one compose file, such as `odctl recreate storage kafka-lite`. They ran every file as one project, so `recreate` failed with `Conflict. The container name "/seaweed" is already in use`, and `restart` and `logs` left out the containers of all but one file. Each file now runs as its own project, as with `odctl up`. [Apply a Change](../how-it-works.md#apply-a-change) uses `odctl recreate`.
- `odctl init --force --yes` and `odctl down --all --volumes --yes` run without asking `Are you sure?`, for scripts and CI. `-y` is the short form. See [Stop a Profile](../getting-started.md#stop-a-profile) and [Start Again](../how-it-works.md#start-again).
- [Getting Started](../getting-started.md) runs every command on `kafka-lite`, with its output, and the [home page](../index.md#commands) lists each command with a link to its example.
- Every guide ends with a Runnable Example that names the files to run. [Rolling Windows](../guides/rolling-windows.md) is a page of its own, and the Flink push to Feast moved to [From Flink SQL](../guides/feast-iceberg.md#from-flink-sql) on the Feast guide.
- The animation on [How It Works](../how-it-works.md#what-odctl-up-does) shows its four steps again. Since 1.1.0 it showed steps 1 to 3 for a moment each and then stayed on step 4, because one step was exported 2 pixels narrower and ffmpeg stopped at the change in size.
- The Labs page is hidden until its first lab is published.

## Version 1.2.0

Flink can send rows to an HTTP API, Spark reads Kafka with no extra options, SeaweedFS survives uploads of large models, and the guides cover cases that real projects met.

- Flink's SQL client has the HTTP connector. [From Flink SQL](../guides/feast-iceberg.md#from-flink-sql) on the Feast guide pushes a feature value to Feast.
- Spark has the Kafka connector and the Avro module, so a job reads a topic, including Avro records written with the schema registry, with no `--packages` option. See [Read a Kafka Topic](../guides/spark.md#read-a-kafka-topic) and [Read Avro Records Written with the Schema Registry](../guides/spark.md#read-avro-records-written-with-the-schema-registry).
- [Keep Messages Longer](../guides/kafka.md#keep-messages-longer) shows the broker's one-day and 500 MB retention and how to turn both off for a topic. [Troubleshooting](../troubleshooting.md#older-messages-are-missing) lists the symptom.
- `seaweed` sets `GOMEMLIMIT` to three quarters of its memory limit, so uploads of a model of a few hundred MB no longer end with HTTP 500 and a killed container. [Troubleshooting](../troubleshooting.md#uploads-fail-with-http-500-and-seaweed-exited-with-code-137) says what to do when the limit is still reached, and [How It Works](../how-it-works.md#examples) changes both values together.
- The [MLflow guide](../guides/mlflow.md) has three new sections: [Move the Alias to a New Version](../guides/mlflow.md#move-the-alias-to-a-new-version), which needs `odctl restart mlflow`, [Load a Model from Your Machine](../guides/mlflow.md#load-a-model-from-your-machine) and [Serve a Model That Reads Online Features](../guides/mlflow.md#serve-a-model-that-reads-online-features).
- The docs now say that the packages in `_MLOPS_PIP_DEPS` are installed from PyPI again in every new `mlflow` and `mlflow-serve` container. [How It Works](../how-it-works.md#examples) lists when a new container is made.
- [How It Works](../how-it-works.md#examples) shows how to create a bucket before its profile exists.
- [Rolling Windows](../guides/rolling-windows.md) shows that Flink SQL refuses two different `OVER` windows in one streaming query, and the two ways around it.
- The [Evidently guide](../guides/evidently-reports.md) says what Evidently does not estimate and why NannyML needs Python 3.12.

### Upgrading

- A workspace made by `odctl init` with an earlier release keeps its old `compose-infra.yml`, which has no `GOMEMLIMIT` for `seaweed`. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate storage`.

## Version 1.1.0

Every service is now reachable from your machine only, and the docs have a [Roadmap](roadmap.md) and a [Changelog](changelog.md).

- Every published port binds to `127.0.0.1`, on macOS, Linux and WSL2, so other machines on your network cannot reach the services. [How You Reach a Service](../how-it-works.md#how-you-reach-a-service) says how to open a port when you need to.
- Kafka no longer publishes ports 29092, 29093 and 29094, which were listeners for a minikube cluster.
- An odctl skill and `llms.txt` help an AI assistant choose a profile and reach its services. See [Use It with an AI Assistant](../getting-started.md#use-it-with-an-ai-assistant).
- Eight guides show in a diagram how data moves between their services, and [How It Works](../how-it-works.md) shows what `odctl up` checks and the order it starts services in. The end-to-end tests run every command the guides show.
- The tables of `odctl ps` and `odctl explain` draw straight right borders on rows with port mappings.
- `odctl down --help` says what `--volumes` removes.

### Upgrading

- To reach a service from another machine, run `odctl init`, remove `127.0.0.1:` from the service's port line in `.odctl/compose-*.yml`, and run `odctl recreate <profile>`.
- A Kafka client in minikube cannot use `host.minikube.internal:29092` any more. Add a listener for it to the Kafka service in `.odctl/compose-kafka.yml`.
- A workspace made by `odctl init` with an earlier release keeps its old compose files, which publish on all interfaces and include port 29092. Run `odctl init --force` to copy the new files; it replaces your edits.
