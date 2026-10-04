# How it works

## Profiles and dependencies

`registry.yml` maps each profile to a compose file and lists the profiles it needs directly. `odctl up` follows those lists until nothing new is added. For example, `odctl up flink-lite` also starts `catalog`, which needs `postgres` and `storage`, which need `deps`. It starts `deps` first, `postgres` and `storage` next, `catalog` after them, and the profiles you named last. `odctl up <profile> --dry-run` prints the plan without starting anything, and each [profile page](profiles/index.md) lists what a profile starts.

Commands other than `up`, such as `down`, `ps`, `logs`, `restart` and `recreate`, act only on the profiles you name. They add a dependency only when it is in the same compose file, because Docker Compose rejects the project otherwise.

## Shared jars in the deps volume

The `deps` profile runs one short-lived container, `odctl-init-deps`. It copies connectors, jars and the Prometheus JMX agent into a Docker volume named `odctl-shared-deps`, then exits. The Kafka brokers, Kafka Connect, Flink, Spark and the Iceberg REST catalog mount that volume. The copy writes only missing or changed files and renames each into place, so a running engine never reads a half-written jar.

The `deps` project also creates the `odctl` Docker network that every service joins. Services reach each other by container name on that network, for example `http://catalog:8181`.

## Image tags follow the CLI version

Most services run their project's official image, pinned to an exact version. odctl builds six images of its own and publishes them to `ghcr.io/jaehyeon-kim/odctl/`:

| Image | Contents |
| --- | --- |
| `deps` | Connectors, jars and the Prometheus JMX agent, including the Iceberg REST catalog and the Kafka Connect Iceberg sink |
| `postgres` | PostgreSQL 18 with pgvector, pg_textsearch and PostGIS |
| `airflow` | Airflow with the MLflow and Feast clients and the model runtimes |
| `mlflow` | The MLflow server and model server with the model runtimes |
| `spark` | Spark with the Python clients jobs use |
| `evidently` | The Evidently UI with s3fs, so datasets can be stored on SeaweedFS |

The compose files tag these images `${TAG:-latest}`. `odctl init` writes `TAG=<CLI version>` to `.odctl/.env`, so odctl 0.10.0 runs images tagged `0.10.0`. Without a workspace, `TAG` is unset and the tag is `latest`. A `TAG` set in the shell takes precedence over `.env`.

Upgrading the CLI does not change `.odctl/.env`. `odctl up` then warns that the workspace's `TAG` differs from the CLI version. `odctl init --force` moves the workspace to the new version, and it also resets your edits.

## Data does not survive `odctl down`

Services keep their data inside their containers. `odctl down` removes the containers, so databases, buckets, topics and Iceberg tables are gone afterwards. Spark's event logs are on `spark-events-data`, a volume held in memory, so they go too. The only volume that outlasts `odctl down` is `odctl-shared-deps`, which holds no data of yours, and `odctl down --volumes` removes it.

`odctl restart` keeps the containers, so data survives it. `odctl recreate` replaces them, so data does not. Use `recreate` to apply an edited compose file, because a restart never applies a new memory limit, port, image tag or environment variable.

## Workspace directory

odctl reads its compose files, `registry.yml` and `.env` from `.odctl` in the current directory when that directory exists. Otherwise it reads the files bundled with the CLI. `--workspace PATH` points it at another directory. [Customise the workspace](guides/workspace.md) lists what you can change there.
