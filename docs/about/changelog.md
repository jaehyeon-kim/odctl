# Changelog

Each release, newest first: what changed, then under Upgrading what to change in commands, workspaces or clients that use the previous release. Releases up to 1.0.2 are described on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).

## Version 1.2.0

Flink can send rows to an HTTP API, Spark reads Kafka with no extra options, SeaweedFS survives uploads of large models, and the guides cover cases that real projects met.

- Flink's SQL client has the HTTP connector. [Send rows to an HTTP API](../guides/flink-sql.md#send-rows-to-an-http-api) pushes a feature value to Feast.
- Spark has the Kafka connector and the Avro module, so a job reads a topic, including Avro records written with the schema registry, with no `--packages` option. See [Read a Kafka topic](../guides/spark.md#read-a-kafka-topic) and [Read Avro records written with the schema registry](../guides/spark.md#read-avro-records-written-with-the-schema-registry).
- [Keep messages longer](../guides/kafka.md#keep-messages-longer) shows the broker's one-day and 500 MB retention and how to turn both off for a topic. [Troubleshooting](../troubleshooting.md#older-messages-are-missing) lists the symptom.
- `seaweed` sets `GOMEMLIMIT` to three quarters of its memory limit, so uploads of a model of a few hundred MB no longer end with HTTP 500 and a killed container. [Troubleshooting](../troubleshooting.md#uploads-fail-with-http-500-and-seaweed-exited-with-code-137) says what to do when the limit is still reached, and [How it works](../how-it-works.md#examples) changes both values together.
- The [MLflow guide](../guides/mlflow.md) has three new sections: [Move the alias to a new version](../guides/mlflow.md#move-the-alias-to-a-new-version), which needs `odctl restart mlflow`, [Load a model from your machine](../guides/mlflow.md#load-a-model-from-your-machine) and [Serve a model that reads online features](../guides/mlflow.md#serve-a-model-that-reads-online-features).
- The text on `_MLOPS_PIP_DEPS` now says that every new `mlflow` and `mlflow-serve` container installs the packages from PyPI again. [How it works](../how-it-works.md#examples) and the MLflow guide have the details.
- [How it works](../how-it-works.md#examples) shows how to create a bucket before its profile exists.
- [Several rolling windows](../guides/flink-sql.md#several-rolling-windows) shows that Flink SQL refuses two different `OVER` windows in one streaming query, and the two ways around it.
- The [Evidently guide](../guides/evidently-reports.md) says what Evidently does not estimate and why NannyML needs Python 3.12.

### Upgrading

- A workspace made by `odctl init` with an earlier release keeps its old `compose-infra.yml`, which has no `GOMEMLIMIT` for `seaweed`. Run `odctl init --force` to copy the new files; it replaces your edits, so keep a copy of them. Then run `odctl recreate storage`.

## Version 1.1.0

Every service is now reachable from your machine only, and the docs have a [Roadmap](roadmap.md) and a [Changelog](changelog.md).

- Every published port binds to `127.0.0.1`, on macOS, Linux and WSL2, so other machines on your network cannot reach the services. [How you reach a service](../how-it-works.md#how-you-reach-a-service) says how to open a port when you need to.
- Kafka no longer publishes ports 29092, 29093 and 29094, which were listeners for a minikube cluster.
- An odctl skill and `llms.txt` help an AI assistant choose a profile and reach its services. See [Use it with an AI assistant](../getting-started.md#use-it-with-an-ai-assistant).
- Eight guides show in a diagram how data moves between their services, and [How it works](../how-it-works.md) shows what `odctl up` checks and the order it starts services in. The end-to-end tests run every command the guides show.
- The tables of `odctl ps` and `odctl explain` draw straight right borders on rows with port mappings.
- `odctl down --help` says what `--volumes` removes.

### Upgrading

- To reach a service from another machine, run `odctl init`, remove `127.0.0.1:` from the service's port line in `.odctl/compose-*.yml`, and run `odctl recreate <profile>`.
- A Kafka client in minikube cannot use `host.minikube.internal:29092` any more. Add a listener for it to the Kafka service in `.odctl/compose-kafka.yml`.
- A workspace made by `odctl init` with an earlier release keeps its old compose files, which publish on all interfaces and include port 29092. Run `odctl init --force` to copy the new files; it replaces your edits.
