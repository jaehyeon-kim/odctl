# Projects

These projects run on odctl. Each entry says what the project builds, which profiles it starts and what it relies on from odctl. Their own READMEs have the steps.

Several projects pin an older odctl in their `requirements.txt` or README. Profile names have changed since some of those versions: odctl 0.9.0 folded `mlflow-serve` into `mlflow` and `feast-serve` into `feast`, and 0.4.x had a `ray-serve` profile that later versions do not. The profiles the projects below use have kept their names, so their `odctl up` commands work on the current version.

## Streaming

### order-streams

Four Kotlin applications produce, consume and aggregate one stream of order events. They start with the plain Kafka clients in JSON, move to Avro with the schema registry, and then compute supplier statistics in 5-second windows with Kafka Streams and with Flink running inside the application.

- Profiles: `kafka-lite`.
- From odctl: the broker on `127.0.0.1:9092`, Karapace on `http://127.0.0.1:8081` and Kafka UI on `http://127.0.0.1:8086`, which the applications use by default.
- Pins: odctl 0.9.0.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/order-streams), [Kafka clients with JSON](https://jaehyeon.me/blog/2025-05-20-kotlin-getting-started-kafka-json-clients/), [Kafka clients with Avro](https://jaehyeon.me/blog/2025-05-27-kotlin-getting-started-kafka-avro-clients/).

### ecommerce-cdc

A simulated online shop writes to PostgreSQL. Debezium reads every change from PostgreSQL's write-ahead log and sends it to Kafka in Avro, and the Aiven S3 sink saves the changes as JSON lines files in SeaweedFS.

- Profiles: `postgres`, `kafka-lite`, `storage`.
- From odctl: PostgreSQL runs with `wal_level=logical` and has the `cdc` schema and the `cdc_pub` publication, and Kafka Connect ships the Debezium PostgreSQL source and the Aiven S3 sink.
- Pins: odctl 0.9.0. odctl 0.10.0 moves Debezium from 3.5.1 to 3.7.0.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/ecommerce-cdc), [post](https://jaehyeon.me/blog/2026-10-01-ecommerce-cdc-debezium-kafka-connect/).

### game-leaderboard

A simulated mobile game sends scores to Kafka in Avro. Four Flink SQL jobs keep four top 10 leaderboards up to date in PostgreSQL, and a NiceGUI dashboard shows them.

- Profiles: `kafka-lite`, `flink-lite`, `postgres`.
- From odctl: Flink's `lib` folder has the Kafka, Avro with Confluent schema registry, and JDBC connectors, and checkpoints go to `s3://flink-checkpoints`.
- Pins: odctl 0.9.0, which ran Flink 2.1. odctl 0.10.0 runs Flink 2.2.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/game-leaderboard), [post](https://jaehyeon.me/blog/2026-10-02-game-leaderboard-flink-sql/).

### live-dashboard

A simulated shop writes its orders to PostgreSQL. A FastAPI WebSocket server pushes the last five minutes of order items to two dashboards, one in Streamlit and one in Next.js.

- Profiles: `postgres`.
- From odctl: PostgreSQL on `127.0.0.1:5432`, database `odctl`, user `user` and password `password`.
- Pins: odctl 0.9.0.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/live-dashboard), [part 1](https://jaehyeon.me/blog/2025-02-18-realtime-dashboard-1/), [part 2](https://jaehyeon.me/blog/2025-02-25-realtime-dashboard-2/).

## ML and MLOps

### air-quality

An ML system that forecasts daily PM2.5 for the next seven days from simulated weather forecasts. Feature, training and inference pipelines share Iceberg tables through Feast and models through the MLflow registry, and Airflow runs them on a schedule.

- Profiles: `catalog`, `feast`, `mlflow`, `airflow`.
- From odctl: Airflow reads DAGs from `s3://airflow/dags`, installs the packages in `_AIRFLOW_PIP_DEPS`, and already has the PyIceberg, MLflow and Feast registry settings for its tasks.
- Pins: odctl 0.9.0 or later.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/air-quality).

### product-recommender

A contextual bandit recommender that learns from every click. A Python client recommends from models in Valkey and sends each result to Kafka, and a Kotlin Flink job trains the models and writes them back to Valkey.

- Profiles: `kafka-lite`, `flink-full`, `valkey`.
- From odctl: Flink reads the training history from `s3://odctl-dev` on SeaweedFS, which `flink-full` starts, and Valkey takes user `user` and password `password`.
- Pins: odctl 0.9.0. The Flink job is built against Flink 2.1.3, and odctl 0.10.0 runs Flink 2.2.
- Links: [code](https://github.com/jaehyeon-kim/benchtop/tree/main/product-recommender), [prototype](https://jaehyeon.me/blog/2026-01-29-prototype-recommender-with-python/), [event-driven system](https://jaehyeon.me/blog/2026-02-23-productionize-recommender-with-eda/).

## AI engineering

### agentic-analytics-system

A Strands agent answers questions over an Iceberg lakehouse through the WrenAI semantic layer, which runs its SQL on Trino. Mem0 keeps each user's preferences in Valkey.

- Profiles: `trino`, `storage`, `catalog`, `valkey`.
- From odctl: Trino's `iceberg` catalog on `http://127.0.0.1:8080` reads the tables that PyIceberg writes through the REST catalog, and Valkey stores Mem0's memories.
- Pins: odctl 0.4.4.
- Links: [code](https://github.com/jaehyeon-kim/agentic-analytics-system), [post](https://jaehyeon.me/blog/2026-07-18-agentic-analytics-system/).

## Data generation

### dynamic-des

A Python library for discrete-event simulations whose parameters change while they run. It writes the simulated data to Kafka, PostgreSQL, Redis, Parquet or Iceberg, and the projects above use it to generate their data. Its examples come in a declarative and an imperative style, and version 0.16.0 adds YAML blueprints run with the `dynamic-des run` command. The latest release on PyPI is 0.15.0.

- Profiles: `kafka-lite`, `postgres`, `valkey`, `storage` and `catalog`, one per example.
- From odctl: each example's default addresses and credentials are the odctl ones, such as `redis://user:password@localhost:6379/0` for Valkey.
- Pins: odctl 0.5.1 or later, because earlier versions created the Valkey user without permission to subscribe to channels.
- Links: [code](https://github.com/jaehyeon-kim/dynamic-des), [documentation](https://jaehyeon.me/dynamic-des/), [digital twin with Flink](https://jaehyeon.me/blog/2026-04-21-digital-twin-online-machine-learning/), [digital twins in Industry 4.0](https://jaehyeon.me/blog/2026-04-23-digital-twin-industry-4-0/).
