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
