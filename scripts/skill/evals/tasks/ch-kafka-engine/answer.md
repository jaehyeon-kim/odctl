# ch-kafka-engine

Answer sheet of the case `ch-kafka-engine`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A6 (service behaviour stated without a run or its source), A2 (service called before it is ready), A12 (a number given with no reason), A10 (a check that cannot fail).

## Records

- github `jaehyeon-kim/odctl#20`: a Kafka address meant for another network (A3).
- planning `odctl/release/1.4.0/review-batch1-round2.md:7` (S3) and `odctl/release/1.7.0/review-round1.md:8` (B-S1): a service's behaviour described from memory (A6).
- planning `odctl/release/1.7.0/review-round1.md:7` (A-S1): containers that run taken to mean the data is stored (A2).
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit (A2).
- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1): a check that could not fail (A10).

## Right answer

- `odctl up kafka-full ch-full` if anything is not running (`registry.yml:71`, `175`).
- The SQL runs with `docker exec -i ch-11 clickhouse-client --password password --multiquery < page_views.sql` or one `-q` per statement (`docs/snippets/clickhouse/commands.sh:10-17`), or over HTTP from the host at `127.0.0.1:8123`, one statement per request, because the HTTP interface refuses several statements in one request with "Multi-statements are not allowed" (ClickHouse `v25.12.9.61-stable`, `src/Parsers/parseQuery.cpp:379-385`).
- Broker list, inside the `odctl` network: `kafka_broker_list = 'broker-1:19092,broker-2:19093,broker-3:19094'` (`registry.yml:91`; `docs/guides/kafka.md:74`), or `broker-1:19092` alone. The ClickHouse servers are on that network (`compose-analytics.yml:5-6`). `kafka_format = 'JSONEachRow'`, a `kafka_group_name` of the run's choice.
- A Kafka engine table streams only while a materialized view reads from it (ClickHouse tag `v25.12.9.61-stable`, `src/Storages/Kafka/StorageKafka.cpp:570-582` and `StorageKafkaUtils.cpp:541-561`), and a direct `SELECT` from it is refused by default (`stream_like_engine_allow_direct_select` is false, `src/Core/Settings.cpp:716-719`). So: a target `MergeTree` (or `ReplicatedMergeTree`) table, the Kafka table, and a materialized view `TO` the target, the target first.
- With no offset stored for the group, the engine starts at the earliest message (`src/Storages/Kafka/KafkaConfigLoader.cpp:476`), so the messages already in the topic are read with no extra setting.
- Rows reach the target in blocks, flushed every `stream_flush_interval_ms` (7500 ms by default, `Settings.cpp:2319-2322`) unless `kafka_flush_interval_ms` is set (`KafkaSettings.cpp:40`; `StorageKafka.cpp:689-691`). The check repeats its count until it is above 0 (or reaches the number of messages in the topic, read with `kafka-get-offsets.sh` in `kafka-1`), with a limit longer than that interval and its reason, and exits 1 when the limit passes. A count that exits 0 when it returns 0 cannot fail.
- If the Kafka table is created on several servers with one group name, Kafka splits the topic's partitions between them (3 by default, `compose-kafka.yml:83`), so a count on one server's target table can miss rows; the check then counts on every server or through a `Distributed` table. Kafka's group assignment, not read in source here: inferred.

## Wrong answers seen or expected

- A3: `127.0.0.1:9092`, `localhost:9092`, `kafka:9092` or `kafka-1:9092` in `kafka_broker_list`; `kafka-full` has no host named `kafka`, and the brokers' internal ports are 19092 to 19094.
- A6: `SELECT` from the Kafka table as the check, or a statement that the Kafka table stores rows; a statement that messages already in the topic are skipped, or a setting added with that reason.
- A1 (counted, not a kind of this case's focus): the materialized view before its target table.
- A2: one count straight after the SQL; a wait with no limit.
- A12: a wait limit or interval with no reason.
- A10: a check that prints the count and exits 0.
- A6: the whole of `page_views.sql` posted to the HTTP interface in one request, which fails with "Multi-statements are not allowed".
