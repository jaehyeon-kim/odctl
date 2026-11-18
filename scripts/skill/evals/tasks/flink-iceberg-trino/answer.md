# flink-iceberg-trino

Answer sheet of the case `flink-iceberg-trino`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A6 (service behaviour stated without a run or its source), A1 (a step needs an earlier step), A2 (service called before it is ready), A12 (a number given with no reason), A3 (address from the wrong side).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:7` (S3) and `odctl/release/1.2.0/review-batch1.md:21`: a service's write behaviour described from memory, here the Iceberg sink's commit (A6).
- planning `architecting-analytics/review-labs.md:159` (V4): `odctl up trino` assumed to start `catalog` and `storage` (A1).
- planning `odctl/release/1.7.0/review-round1.md:7` (A-S1): healthy containers taken to mean the data is stored (A2).
- github `jaehyeon-kim/odctl#20` and planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the wrong side (A3).
- A12 extends the evidence of `planning/odctl/plan-agent-skill.md:30`: a checkpoint interval and a wait limit the agent picks.

## Right answer

- `odctl up flink-full kafka-full trino`: `flink-full` brings `catalog`, which brings `postgres` and `storage` (`registry.yml:98-99`, `58`), and `trino` brings `postgres` (`registry.yml:176`); `odctl up flink-full kafka-full trino --dry-run` lists `deps`, `postgres`, `storage`, `catalog`, `flink-full`, `kafka-full` and `trino`. `kafka-full` is already running, and naming it again is harmless.
- The SQL runs in the JobManager container: `docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh < clicks.sql`, as `docs/guides/fluss.md:89` and `smoke.sh:358-359` pipe it, or `docker cp` and `sql-client.sh -f`, or the SQL Gateway at `http://127.0.0.1:8084` (`registry.yml:113-115`). Each client run is one session, so the `CREATE CATALOG` and the `INSERT` are in the same run.
- Kafka source, inside the `odctl` network: `'properties.bootstrap.servers' = 'broker-1:19092,broker-2:19093,broker-3:19094'` (`registry.yml:91`; `docs/guides/kafka.md:74`), or `broker-1:19092` alone; `'format' = 'json'` (flink-json is in Flink's `lib`, apache/flink tag `release-2.2.0`, `flink-dist/src/main/assemblies/bin.xml:119-121`).
- `'scan.startup.mode' = 'earliest-offset'`. The default is `group-offsets`, and with no committed offset the connector's reset strategy defaults to `NONE` (apache/flink-connector-kafka tag `v5.0.0`, `KafkaDynamicSource.java:452-459`; the deps image fetches `flink-sql-connector-kafka` `5.0.0-2.2`, `deps/fetch_flink_dependencies.sh:34-36`), and with that strategy the job fails at run time when the group has no committed offset (`OffsetsInitializer.java:101-105`: "An exception will be thrown at runtime if there is no committed offsets"). So the job reads the messages already in the topic only with `earliest-offset`, or with `group-offsets` and `'properties.auto.offset.reset' = 'earliest'`; both are right.
- Iceberg catalog as `docs/snippets/iceberg-ingestion/steps.sql:8`: `'type'='iceberg'`, `'catalog-type'='rest'`, `'uri'='http://catalog:8181'`, `'warehouse'='s3://warehouse'`, `'s3.endpoint'='http://seaweed:8333'`, path-style access, keys `user` and `password`; then `CREATE DATABASE IF NOT EXISTS` and the table, before the `INSERT`.
- A streaming `INSERT` into Iceberg commits only when a Flink checkpoint completes ("Iceberg commit happened after successful Flink checkpoint in the `notifyCheckpointComplete` callback", apache/iceberg tag `apache-iceberg-1.12.0`, `docs/docs/flink-writes.md:234`). odctl's Flink configuration sets the checkpoint directory but no interval (`flink/flink-conf.yml:13-21`), and `execution.checkpointing.interval` has no default (apache/flink `release-2.2.0`, `CheckpointingOptions.java:511-514`). So the job needs `SET 'execution.checkpointing.interval' = '<n>s';` before the `INSERT`; without it the job runs and Trino never sees a row. The bucket `flink-checkpoints` exists (`compose-infra.yml:109`; `flink/flink-conf.yml:20`).
- Trino, from its container: `docker exec trino trino --execute "SELECT count(*) FROM iceberg.web.clicks"` (`docs/snippets/trino-metabase/commands.sh:14`; catalog `trino/catalog/iceberg.properties`). No `-t`: Docker refuses it when stdin is not a terminal (`planning/odctl/release/1.10.0/progress.md:190`).
- The check waits: the first rows appear only after the first checkpoint completes, and Trino's catalogs load after its health check passes (`smoke.sh:491-493`, `503-507`). It repeats the count until it is above 0, with a limit longer than the checkpoint interval and the job's start, and exits 1 when the limit passes. A count query exits 0 when it returns 0, so a check that only runs the query cannot fail.
- The checkpoint interval and the wait limit each have their reason beside them.

## Wrong answers seen or expected

- A6: a streaming `INSERT` with no checkpoint interval, or a statement that the rows are visible as soon as they are written.
- A6: no `scan.startup.mode` and no `properties.auto.offset.reset`, or a statement that the default reads the topic from the start.
- A1: `CREATE CATALOG` in one client run and the `INSERT` in another; the `INSERT` before the database or table exists; `odctl up trino` alone expected to bring the Iceberg catalog.
- A3: `127.0.0.1:9092`, `localhost:9092`, `kafka:9092`, `http://127.0.0.1:8181` or `http://127.0.0.1:8333` inside the Flink SQL; `iceberg-rest:8181` or `seaweedfs:8333` anywhere.
- A2: a single count straight after the job starts, or a wait with no limit.
- A12: a checkpoint interval or a wait limit with no reason.
- `docker exec -it trino trino` in a script.
