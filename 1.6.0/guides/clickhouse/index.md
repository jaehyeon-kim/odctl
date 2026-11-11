# ClickHouse

ClickHouse is a column-oriented database for analytical queries. A shard holds part of a table's rows, and each replica of a shard holds a copy of that part. ClickHouse Keeper is the coordination service that keeps the replicas of a shard in step. The `ch-lite` profile runs one shard with two replicas, `ch-11` and `ch-12`, coordinated by ClickHouse Keeper in `ch-keeper`. `ch-full` adds a second shard, `ch-21` and `ch-22`. The end-to-end tests run the commands below on every release.

This guide builds on [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md). Start the profile:

```bash
odctl up ch-lite
```

| Endpoint                      | Address                                                                                                                       |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| HTTP from the host            | `http://127.0.0.1:8123` (`ch-11`) and `http://127.0.0.1:8124` (`ch-12`); `ch-full` adds `8125` (`ch-21`) and `8126` (`ch-22`) |
| Native protocol from the host | `127.0.0.1:9000` (`ch-11`) and `127.0.0.1:9001` (`ch-12`); `ch-full` adds `9002` (`ch-21`) and `9003` (`ch-22`)               |
| Users                         | `default` and `user`, both with the password `password`                                                                       |

Every server creates the `feature_store` and `odctl` databases when it starts with no data.

## Create a Table and Query It

`clickhouse-client` is in each server container. This lists the databases, then creates a table, writes 10 rows and counts them:

```bash
docker exec ch-11 clickhouse-client --password password -q "SHOW DATABASES"

docker exec ch-11 clickhouse-client --password password -q \
  "CREATE TABLE default.demo (id UInt32) ENGINE=MergeTree ORDER BY id"
docker exec ch-11 clickhouse-client --password password -q \
  "INSERT INTO default.demo SELECT number FROM numbers(10)"
docker exec ch-11 clickhouse-client --password password -q \
  "SELECT count() FROM default.demo"
```

The first command lists `default`, `feature_store`, `odctl` and the system databases. The last prints `10`.

ClickHouse also serves a query page at `http://127.0.0.1:8123/play`. Enter `default` and `password` in the top right, write a query and press Run.

## Replicate Across the Cluster

In `ch-full`, `{cluster}` names `odctl_cluster`, which has two shards of two replicas. A table created `ON CLUSTER` with `ReplicatedMergeTree` is created on all four servers, and Keeper keeps the two replicas of each shard in step:

```bash
odctl up ch-full

docker exec ch-11 clickhouse-client --password password -q \
  "CREATE TABLE default.repl ON CLUSTER '{cluster}' (id UInt32) ENGINE=ReplicatedMergeTree ORDER BY id"
docker exec ch-11 clickhouse-client --password password -q \
  "INSERT INTO default.repl SELECT number FROM numbers(50)"

docker exec ch-12 clickhouse-client --password password -q "SELECT count() FROM default.repl"
docker exec ch-21 clickhouse-client --password password -q "SELECT count() FROM default.repl"
```

The `CREATE` prints one line for each of the four servers, with status `0` for success. `ch-12`, the other replica of shard 1, returns `50` once replication has caught up. `ch-21` returns `0`, because shard 2 holds only the rows written to it.

In `ch-lite`, `{cluster}` names `odctl_single_shard`, which holds `ch-11` and `ch-12` only, so `ON CLUSTER` statements finish without waiting for the missing shard.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), connect to `ch-11:8123` over HTTP or `ch-11:9000` with the native protocol, with the same users. Trino's `clickhouse` catalog reads the `feature_store` database on `ch-11`, as [Trino and Metabase](https://jaehyeon.me/odctl/latest/guides/trino-metabase/index.md) shows.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It runs on `ch-lite`, where `{cluster}` holds the two replicas of one shard, and uses tables of its own for each run:

```bash
#!/usr/bin/env bash
# Starts ch-lite, writes 10 rows to a MergeTree table and 50 rows to a
# replicated table, and counts the replicated rows on the other replica.
# Each run uses its own table names.
set -euo pipefail

odctl up ch-lite

run=$(date +%s)
ch() { docker exec "$1" clickhouse-client --password password -q "$2"; }

ch ch-11 "CREATE TABLE default.demo_$run (id UInt32) ENGINE=MergeTree ORDER BY id"
ch ch-11 "INSERT INTO default.demo_$run SELECT number FROM numbers(10)"
ch ch-11 "SELECT count() FROM default.demo_$run"

ch ch-11 "CREATE TABLE default.repl_$run ON CLUSTER '{cluster}' (id UInt32) ENGINE=ReplicatedMergeTree ORDER BY id" >/dev/null
ch ch-11 "INSERT INTO default.repl_$run SELECT number FROM numbers(50)"
# ch-12 is the other replica of the same shard; replication takes a moment.
until [ "$(ch ch-12 "SELECT count() FROM default.repl_$run")" = "50" ]; do sleep 1; done
echo "ch-12 holds 50 rows of repl_$run"
```

It prints `10`, then `ch-12 holds 50 rows of` with the replicated table's name.
