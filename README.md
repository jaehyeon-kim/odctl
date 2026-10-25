# Open Data Stack (odctl)

![CI Status](https://img.shields.io/github/actions/workflow/status/jaehyeon-kim/odctl/pipeline.yml?branch=main&label=CI) ![PyPI Version](https://img.shields.io/pypi/v/odctl) ![Python Versions](https://img.shields.io/pypi/pyversions/odctl) ![License](https://img.shields.io/github/license/jaehyeon-kim/odctl)

**Run an open data stack on your machine, with its services already connected, from one command.**

![odctl architecture](https://raw.githubusercontent.com/jaehyeon-kim/odctl/refs/heads/main/image/diagram.png)

odctl is a command-line tool that runs an open data stack on your machine with Docker Compose: Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, MLflow, Feast, Airflow and more. You name the profiles you want, such as `kafka-lite` or `airflow`, and odctl starts them together with the services they depend on.

To see why it exists and how it differs from a Compose file of your own, read [Why odctl](https://jaehyeon.me/odctl/latest/about/why-odctl/).

Documentation: [jaehyeon.me/odctl](https://jaehyeon.me/odctl/). It covers every profile with its ports, images and memory limits, the CLI reference, guides and troubleshooting.

## Installation

odctl needs Docker running and Python 3.10 or later. [Requirements](https://jaehyeon.me/odctl/latest/getting-started/#requirements) says how much memory to give Docker. Install odctl into its own environment:

```bash
uv tool install odctl
# or
pipx install odctl
```

## Quick Start

These commands create a workspace, list the profiles, start three of them and stop everything:

```bash
odctl init                    # copy the compose files and settings into ./.odctl
odctl list                    # show the profiles
odctl up kafka-lite flink-lite spark-lite
odctl down --all
```

`odctl up` starts the profiles each one depends on first, here PostgreSQL, SeaweedFS (S3) and the Iceberg REST catalog. See [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/) for more.

![Installing odctl, previewing what flink-lite starts, starting kafka-lite, listing the containers and stopping them](https://raw.githubusercontent.com/jaehyeon-kim/odctl/refs/heads/main/image/demo.gif)

## Commands

Each command has its own section in the CLI reference, with its options and examples. The Example column links to a page that runs the command and shows its output, and [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/) runs them in order on one profile.

| Command | Use it to | Example |
| --- | --- | --- |
| [`odctl list`](https://jaehyeon.me/odctl/latest/cli/#odctl-list) | See every profile and what it runs | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile) |
| [`odctl explain`](https://jaehyeon.me/odctl/latest/cli/#odctl-explain) | See a profile's services, images, ports and the profiles it depends on | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile) |
| [`odctl ps`](https://jaehyeon.me/odctl/latest/cli/#odctl-ps) | See the running containers, their health and their ports | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl info`](https://jaehyeon.me/odctl/latest/cli/#odctl-info) | Check the installed odctl version and whether Docker is reachable | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl init`](https://jaehyeon.me/odctl/latest/cli/#odctl-init) | Copy the compose files and settings into `.odctl`, so you can edit them | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#create-a-workspace) |
| [`odctl pull`](https://jaehyeon.me/odctl/latest/cli/#odctl-pull) | Download a profile's images before you start it | [How It Works](https://jaehyeon.me/odctl/latest/how-it-works/#which-images-run) |
| [`odctl up`](https://jaehyeon.me/odctl/latest/cli/#odctl-up) | Start profiles and the profiles they depend on | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#start-a-profile) |
| [`odctl down`](https://jaehyeon.me/odctl/latest/cli/#odctl-down) | Stop profiles and remove their containers | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#stop-a-profile) |
| [`odctl logs`](https://jaehyeon.me/odctl/latest/cli/#odctl-logs) | Read the logs of a profile's containers | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#see-what-is-running) |
| [`odctl restart`](https://jaehyeon.me/odctl/latest/cli/#odctl-restart) | Restart a profile's containers and keep them | [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#restart-a-profile) |
| [`odctl recreate`](https://jaehyeon.me/odctl/latest/cli/#odctl-recreate) | Replace a profile's containers, to apply an edit to a compose file or `.env` | [How It Works](https://jaehyeon.me/odctl/latest/how-it-works/#examples) |

## Roadmap

odctl follows semantic versioning from 1.0, so a later 1.x release does not break a project that pins `odctl>=1.0,<2`. The next releases add an MCP endpoint and streaming features for Feast, custom OpenMetadata connectors, a written list of what 1.x keeps stable with JSON output, an MCP server for AI agents, a Langfuse profile, and snapshot and restore of a profile's data. The [roadmap page](https://jaehyeon.me/odctl/latest/about/roadmap/) shows each step in order.

## Related Reading

Blog posts about odctl and the projects built on it are tagged [odctl](https://jaehyeon.me/tags/odctl/) on jaehyeon.me.

Projects that use odctl:

- [benchtop](https://github.com/jaehyeon-kim/benchtop): hands-on data engineering and machine learning demos that run locally, each on the odctl stack.
- [desflow](https://github.com/jaehyeon-kim/desflow) ([docs](https://jaehyeon.me/desflow/)): a SimPy library for simulations that stream to Kafka, PostgreSQL, Redis and Iceberg; its examples and integration tests run their infrastructure with odctl.
- [agentic-analytics-system](https://github.com/jaehyeon-kim/agentic-analytics-system): conversational analytics over an Iceberg lakehouse, with Trino, Iceberg and object storage started by odctl.

## Contributing

Pull requests are welcome. [CONTRIBUTING.md](https://github.com/jaehyeon-kim/odctl/blob/main/CONTRIBUTING.md) explains how to set up the repository, run the tests, add a profile or a command, and write the docs.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
