# Open Data Stack

![CI Status](https://img.shields.io/github/actions/workflow/status/jaehyeon-kim/odctl/pipeline.yml?branch=main&label=CI)
![PyPI Version](https://img.shields.io/pypi/v/odctl)
![Python Versions](https://img.shields.io/pypi/pyversions/odctl)
![License](https://img.shields.io/github/license/jaehyeon-kim/odctl)

![Architecture Diagram](https://raw.githubusercontent.com/jaehyeon-kim/odctl/refs/heads/main/image/diagram.png)

A curated collection of open-source technologies and an accompanying CLI (`odctl`) for experimenting with modern data architecture and MLOps locally.

Provisioning a local data environment with distributed systems can be highly complex. The Open Data Stack streamlines this process by resolving dependency conflicts, network routing configurations, and integration challenges across tools like Kafka, Spark, Flink, Iceberg, and Airflow. It provides a cohesive, Docker-based blueprint that operates seamlessly out of the box.

Documentation: [jaehyeon.me/odctl](https://jaehyeon.me/odctl/). It covers every profile with its ports, images and memory limits, the CLI reference, guides and troubleshooting.

## Installation

odctl needs Docker running, with 8 to 16 GB of memory, and Python 3.10 or later. Install it into its own environment:

```bash
uv tool install odctl
# or
pipx install odctl
```

## Quick Start

```bash
odctl init                    # copy the compose files and settings into ./.odctl
odctl list                    # show the profiles
odctl up kafka-lite flink-lite spark-lite
odctl down --all
```

`odctl up` starts the profiles each one depends on first, here PostgreSQL, SeaweedFS (S3) and the Iceberg REST catalog. See [Getting started](https://jaehyeon.me/odctl/latest/getting-started/) for more.

## Related reading

Blog posts that use this CLI:

- [Productionizing an Online Product Recommender using Event Driven Architecture](https://jaehyeon.me/blog/2026-02-23-productionize-recommender-with-eda/): splits a contextual bandit recommender into a serving layer and a training layer on Kafka, Flink and Valkey.
- [Introducing odctl: One CLI for a Local Open Data Stack](https://jaehyeon.me/blog/2026-07-16-odctl-open-data-stack/): why the tool exists and how one command launches the stack.
- [Building an Agentic Analytics System over an Iceberg Lakehouse](https://jaehyeon.me/blog/2026-07-18-agentic-analytics-system/): runs Trino, Iceberg and object storage from this CLI under a semantic layer an agent queries.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
