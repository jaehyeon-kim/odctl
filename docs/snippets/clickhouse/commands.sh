# Commands from docs/guides/clickhouse.md. .github/scripts/smoke.sh runs each section.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up ch-lite
# --8<-- [end:up]

# --8<-- [start:merge-tree]
docker exec ch-11 clickhouse-client --password password -q "SHOW DATABASES"

docker exec ch-11 clickhouse-client --password password -q \
  "CREATE TABLE default.demo (id UInt32) ENGINE=MergeTree ORDER BY id"
docker exec ch-11 clickhouse-client --password password -q \
  "INSERT INTO default.demo SELECT number FROM numbers(10)"
docker exec ch-11 clickhouse-client --password password -q \
  "SELECT count() FROM default.demo"
# --8<-- [end:merge-tree]

# --8<-- [start:replicated]
odctl up ch-full

docker exec ch-11 clickhouse-client --password password -q \
  "CREATE TABLE default.repl ON CLUSTER '{cluster}' (id UInt32) ENGINE=ReplicatedMergeTree ORDER BY id"
docker exec ch-11 clickhouse-client --password password -q \
  "INSERT INTO default.repl SELECT number FROM numbers(50)"

docker exec ch-12 clickhouse-client --password password -q "SELECT count() FROM default.repl"
docker exec ch-21 clickhouse-client --password password -q "SELECT count() FROM default.repl"
# --8<-- [end:replicated]
