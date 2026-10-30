# Changelog

Each release, newest first: what changed, then under Upgrading what to change in commands, workspaces or clients that use the previous release. Releases up to 1.0.2 are described on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).

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
- Every guide ends with a Runnable Example that names the files to run. [Rolling Windows](../guides/rolling-windows.md) is a page of its own, and the Flink push to Feast moved to [Push Features from Flink SQL](../guides/feast-iceberg.md#from-flink-sql).
- The animation on [How It Works](../how-it-works.md#what-odctl-up-does) shows its four steps again. Since 1.1.0 it showed steps 1 to 3 for a moment each and then stayed on step 4, because one step was exported 2 pixels narrower and ffmpeg stopped at the change in size.
- The Labs page is hidden until its first lab is published.

## Version 1.2.0

Flink can send rows to an HTTP API, Spark reads Kafka with no extra options, SeaweedFS survives uploads of large models, and the guides cover cases that real projects met.

- Flink's SQL client has the HTTP connector. [Push Features from Flink SQL](../guides/feast-iceberg.md#from-flink-sql) pushes a feature value to Feast.
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
