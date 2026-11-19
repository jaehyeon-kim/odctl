---
name: odctl
description: Starts a local open data stack with odctl, reaches its services from the host and from containers, and runs it in a project's tests or CI. Use when a task needs Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, Metabase, PostgreSQL, SeaweedFS, MLflow, Feast, Evidently, Label Studio, Airflow, Temporal, Marquez, OpenMetadata, Valkey, Fluss, Langfuse or Grafana running locally in Docker, or code that connects to them.
---

# odctl

odctl starts open source data services as Docker Compose profiles. Install it with `uv tool install odctl` or `pipx install odctl`; it needs Docker. The Commands, Options and Workspace Settings tables below and [references/profiles.md](references/profiles.md) are generated from odctl's CLI, `registry.yml` and compose files.

- [references/profiles.md](references/profiles.md): each profile's addresses from the host and from a container, its logins, services and ports, what it also starts and where its data lives. Read the section of every profile the task uses.
- [references/testing.md](references/testing.md): odctl in a project's tests and CI. Read it when a test, a CI job or a setup script starts the stack.

## Checklist

Copy this checklist into your reply and tick each line as you go:

```text
- [ ] List every service the task needs, one line each.
- [ ] For each, name its profile, its address from where the code runs (host or container), and whether `odctl up` waits for it (the profile's Health line) or the code must wait for it.
- [ ] Run odctl up <profiles> --dry-run, then odctl up <profiles>.
- [ ] Run each step of a guide in the order the guide gives, after the steps it needs.
```

## How to Use It

- Start what the task needs with `odctl up <profile> [<profile> ...]`. Each profile also starts the profiles it depends on, and `odctl up` returns once every service is running, and healthy where it has a health check. `odctl recreate` waits the same way; `odctl restart` does not wait. Each profile's Health line in [references/profiles.md](references/profiles.md) names the services it waits for and their checks. After `odctl up` or `odctl recreate`, call such a service once, with no wait loop and no extra probe: PostgreSQL's connection, ClickHouse's `SELECT 1`, Feast's `/health`, MLflow serving's `/ping` and Langfuse's `/api/public/health` are their health checks.
  - Wrong: `odctl up trino`, then a loop on `http://127.0.0.1:8080/v1/info`, which is the health check `odctl up` already waited for.
  - Wrong: `odctl up postgres`, then a test fixture that retries the connection 12 times.
  - Right: `odctl up trino`, then the task's first query.
- Some services have no health check, so `odctl up` returns once they run, before they answer: Kafka's brokers, Kafka Connect and Karapace, the Iceberg REST `catalog`, Fluss's `fluss-tablet-1`, Flink's SQL gateway and task managers, and Spark's workers. Never say `odctl up` waited until they are healthy. Wait for what the task needs from them, and for what a service finishes later, such as a DAG parsed or a job's rows committed, with a check and a limit, not a fixed time.
  - Wrong: `sleep 10`, a wait on Grafana's `/api/health`, or "`odctl up catalog` returns once the catalog is healthy", then a call to it with no wait.
  - Right: after `odctl up catalog`, retry `curl -fsS http://127.0.0.1:8181/v1/config` every 5 seconds, up to 12 times, before the first call. After `odctl up kafka-lite`, retry `docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 --list` the same way before the first topic is created. For Grafana, `curl -fsS -u user:password 'http://127.0.0.1:3004/api/datasources/proxy/uid/prometheus/api/v1/query?query=up'`, piped to a check that `status` is `success` and `data.result` is not empty. `curl -f` alone passes on an empty result.
- `odctl up <profile> --dry-run` prints the profiles it would start, in order, without starting anything. `odctl explain <profile>` shows its services, images and dependencies. Read them rather than guess what a profile starts.
  - Wrong: `odctl up trino` for a query on Iceberg tables, assuming it starts the catalog and the storage.
  - Right: `odctl up trino --dry-run` lists `deps`, `postgres` and `trino`, so start `odctl up trino catalog`.
- `odctl ps --json` and `odctl list --json` print what is running and every profile as JSON, which is easier to read than the tables; the keys stay the same in every 1.x release ([What Stays Stable in 1.x](https://jaehyeon.me/odctl/latest/how-it-works/#what-stays-stable-in-1x)). `odctl ps` needs profile names or `--all`.
  - Wrong: `odctl ps` or `odctl ps --json`, which exits 1.
  - Right: `odctl ps --all --json`, or `odctl ps kafka-lite --json`.
- Use only the commands in the Commands table below, and run `odctl <command> --help` when unsure. odctl starts and stops services; each service's own client runs inside its container.
  - Wrong: `odctl trino`, or `odctl logs feast-serve`, which names a service where `logs` takes a profile.
  - Right: `docker exec trino trino --execute 'SHOW CATALOGS'`, and `odctl logs feast --service feast-serve`.
- With the `mcp` extra, `odctl mcp` serves `list`, `explain`, `ps`, `info` and `logs` to an MCP client as tools, and `odctl mcp --allow-changes` adds `up` and `down` ([MCP Server](https://jaehyeon.me/odctl/latest/guides/mcp-server/)). Use the tools when the client has them, and the commands otherwise.
  - Wrong: `uv tool install odctl`, then `odctl mcp`, which exits 1 without the extra.
  - Right: `uv tool install "odctl[mcp]"`, then `odctl mcp`.
- `odctl down <profile>` stops only the profiles named, not their dependencies. It removes their containers, so their data is lost with or without `--volumes`, PostgreSQL's included: the next `odctl up` starts again from a clean state. `--volumes` also deletes the old volumes from disk, such as the unnamed volumes PostgreSQL leaves unused, Spark's `spark-events-data`, and the shared jar volume `odctl-shared-deps` once no other profile has a container. `odctl recreate` keeps the data of PostgreSQL, SeaweedFS, ClickHouse with its Keeper, and Fluss's ZooKeeper, and loses the rest. A service that keeps its data in a database of `postgres`, such as Airflow, Metabase, Marquez or the catalog, keeps it through `odctl down` and `odctl recreate` of its own profile while `postgres` runs. Each profile's section in [references/profiles.md](references/profiles.md) says where its data lives.
  - Wrong: "`odctl down postgres` keeps the databases; add `--volumes` only if you want the data removed."
  - Wrong: "`odctl down metabase` deletes the dashboards." Metabase keeps them in the `metabase` database of `postgres`, which keeps running.
  - Wrong: "`odctl down feast` removes the features in Valkey." `valkey` is a dependency of `feast`, so it keeps running.
  - Right: "`odctl down postgres` removes the databases, with or without `--volumes`, and `odctl down kafka-lite` removes the topics. `odctl recreate postgres` keeps the databases."
- Stop and remove only the profiles the task started. To also free the disk the old volumes take, run `odctl down <profiles> --volumes --dry-run` first, which lists the volumes `--volumes` would remove, then the same command without `--dry-run`. `odctl init --force` asks for confirmation, and so does `odctl down --volumes` with `--all`, or with profiles that, with their dependencies, are every profile with containers; a CI script, where no one can answer, passes `--yes` to those. Any other `odctl down` asks nothing.
  - Wrong: `odctl down --all --volumes` at the end of a task that started `kafka-lite`.
  - Wrong: "`--yes` skips the prompt of `odctl down ch-lite --volumes`" while `postgres` still runs; that command asks nothing.
  - Right: `odctl down kafka-lite`.
- Every port is published on `127.0.0.1` only, so other machines cannot reach it. From the host, use `127.0.0.1` and the host port. From a container, join the `odctl` Docker network and use the container name and container port.
  - Wrong: `localhost:9092` from a Spark job in a container.
  - Right: `broker-1:19092` from a container on the `odctl` network, `127.0.0.1:9092` from the host.
- Take host names, ports and logins from the profile's notes in [references/profiles.md](references/profiles.md), never from the upstream image's defaults. Most services use the user `user` and the password `password`; some have no login.
  - Wrong: `seaweedfs:8333` with `admin/admin`.
  - Right: `http://seaweed:8333` from a container, with `user` and `password`, as the `storage` notes give.
- `odctl init` copies the compose files, `registry.yml` and `.env` into `.odctl/` in the current directory, so they can be edited. Run `odctl recreate <profile>` after editing a compose file or `.env`. `odctl init --force` replaces the whole workspace, edits included. It changes only the files in `.odctl/`, not a container, a volume or a database.
  - Wrong: `odctl restart mlflow` after changing `_MLOPS_PIP_DEPS` in `.odctl/.env`; a restart keeps the container and its old settings.
  - Right: `odctl recreate mlflow`.
  - Wrong: "`odctl init --force` deletes Airflow's run history." The history is in the `airflow` database of `postgres`.
- `-lite` profiles run one node of a tool; `-full` profiles run a cluster of it. Start one of the pair, not both.
  - Wrong: `odctl up kafka-lite kafka-full`.
  - Right: `odctl up kafka-lite`, or `odctl up kafka-full` when the task needs three brokers.

## Commands

| Command | Does |
| --- | --- |
| `odctl list` | List all available profiles and their capabilities. |
| `odctl explain` | Explain the details, services, images, and dependencies of a profile. |
| `odctl init` | Initialize a local .odctl workspace for custom configurations. |
| `odctl pull` | Pre-fetch Docker images without starting the containers. |
| `odctl up` | Launch Open Data profiles. |
| `odctl down` | Stop and remove profile containers and networks. |
| `odctl ps` | List Docker containers managed by the Open Data Stack. |
| `odctl info` | Show the odctl version, whether Docker is reachable and, with `--json`, the image tag, the workspace and odctl's own images. |
| `odctl logs` | Fetch the logs of containers managed by specific profiles. |
| `odctl restart` | Restart one or more specific profiles. |
| `odctl recreate` | Replace one or more profiles' containers, applying compose file changes. |
| `odctl mcp` | Serve odctl's commands to an AI agent as MCP tools over stdio. |

## Options

Global options go before the command, as in `odctl --workspace ../shared/.odctl ps --all`.

| Command | Option | Does |
| --- | --- | --- |
| global | `--verbose` | Enable debug-level logging across all commands. |
| global | `--workspace, -w` | Path to the odctl workspace directory (default: ./.odctl). |
| `odctl list` | `--details, -d` | Inspect docker-compose files to show exact services and exposed host ports. |
| `odctl list` | `--json` | Print the output as JSON, for scripts and AI assistants. |
| `odctl explain` | `--json` | Print the output as JSON, for scripts and AI assistants. |
| `odctl init` | `--force, -f` | Wipe out the existing workspace and recreate it from scratch. |
| `odctl init` | `--yes, -y` | Answer yes to the confirmation prompt, for scripts and CI. |
| `odctl pull` | `--all, -a` | Pull images for ALL available profiles in the registry. |
| `odctl up` | `--dry-run` | Preview the execution plan without actually starting anything. |
| `odctl up` | `--pull` | Pull the images again before starting, to fetch a tag that changed in the registry. |
| `odctl down` | `--all, -a` | Stop ALL running profiles. |
| `odctl down` | `--volumes, -v` | Also remove the volumes of the stopped containers, named and unnamed, and the shared jar volume once no other profile uses it. |
| `odctl down` | `--dry-run` | Preview the teardown plan, with the volumes `--volumes` would remove, without stopping anything. |
| `odctl down` | `--yes, -y` | Answer yes to the confirmation prompt, for scripts and CI. |
| `odctl ps` | `--all, -a` | Show all containers managed by odctl. |
| `odctl ps` | `--json` | Print the output as JSON, for scripts and AI assistants. |
| `odctl info` | `--json` | Print the output as JSON, for scripts and AI assistants. |
| `odctl logs` | `--service, -s` | Filter to a specific compose service (Use 'odctl ps' to find names). |
| `odctl logs` | `--follow, -f` | Follow log output in real-time. |
| `odctl logs` | `--tail, -n` | Number of lines to show from the end of the logs. |
| `odctl logs` | `--timestamps, -t` | Show timestamps. |
| `odctl logs` | `--since` | Show logs since timestamp or relative (for example '42m'). |
| `odctl logs` | `--until` | Show logs before a timestamp or relative. |
| `odctl recreate` | `--pull` | Pull images before recreating. |
| `odctl mcp` | `--allow-changes` | Also serve `up` and `down`, which start and stop profiles. |

## Workspace Settings

`odctl init` writes these keys to `.odctl/.env`. Run `odctl recreate <profile>` after changing one.

| Key | Sets |
| --- | --- |
| `TAG` | The tag of odctl's own images, set to the CLI version. A `TAG` in the shell overrides it. |
| `TZ` | The time zone of the services that read it, `UTC` by default. |
| `_AIRFLOW_PIP_DEPS` | Extra Python packages installed in every new Airflow container. |
| `_MLOPS_PIP_DEPS` | Extra Python packages installed in every new `mlflow` and `mlflow-serve` container. |
| `AIRFLOW_OPENLINEAGE_TRANSPORT` | Where Airflow sends OpenLineage events, as JSON such as `{"type": "http", "url": "http://marquez-api:5000"}`; empty means Airflow sends none. |
| `_METADATA_PIP_DEPS` | Extra Python packages installed in every new `openmetadata-ingestion` container. |
| `METADATA_AUTOPILOT` | `true` turns on OpenMetadata's AutoPilot, which creates and runs default agents for a service added in the UI; it is `false` by default. |
| `MODEL_URI` | The model `mlflow-serve` serves, such as `models:/<name>@<alias>`; empty means it waits idle. |
