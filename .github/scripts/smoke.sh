#!/usr/bin/env bash
# Functional smoke test for one odctl profile.
#
# Liveness is not enough: every bug fixed in 0.2.x and 0.3.0 left its containers
# running and healthy while the profile was unusable. Kafka consumer groups hung
# forever, Spark could not start a SparkContext, Flink could not find a connector
# factory, ClickHouse could not consume from the broker, the Trino ClickHouse
# catalog pointed at a hostname that did not exist, and the Flink Iceberg sink
# committed nothing while its checkpoints succeeded. Each assertion below exists
# because something shipped broken past a liveness check.
#
# Usage: smoke.sh <profile>
set -uo pipefail

PROFILE="${1:?usage: smoke.sh <profile>}"

fail() { echo "❌ $PROFILE: $*"; exit 1; }
pass() { echo "✅ $PROFILE: $*"; }

# Retry a command until it succeeds or the budget runs out.
retry() {
  local tries="$1" delay="$2"; shift 2
  for ((i = 1; i <= tries; i++)); do
    if "$@" >/dev/null 2>&1; then return 0; fi
    sleep "$delay"
  done
  return 1
}

http_ok() { curl -fsS -o /dev/null --max-time 10 "$1"; }

# Some endpoints answer 403 or 404 to an unauthenticated probe, which still
# proves the service is listening.
http_reachable() {
  local code
  code=$(curl -s -o /dev/null --max-time 10 -w '%{http_code}' "$1")
  [ -n "$code" ] && [ "$code" != "000" ]
}

ch() { docker exec "$1" clickhouse-client --password password -q "$2" 2>&1; }

kafka_topic() {
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 "$@"
}

smoke_kafka() {
  local container="$1"
  retry 30 5 docker exec "$container" /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server broker-1:19092 --list || fail "broker never became reachable"
  docker exec "$container" /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
    --create --topic smoke --partitions 1 --replication-factor 1 >/dev/null 2>&1
  for i in 1 2 3 4 5; do echo "{\"n\":$i}"; done | docker exec -i "$container" \
    /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic smoke >/dev/null 2>&1 \
    || fail "produce failed"
  # Group mode on purpose. Assign mode bypasses the coordinator and would pass
  # even when __consumer_offsets cannot be created on a single broker.
  local got
  got=$(docker exec "$container" /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server broker-1:19092 --topic smoke --from-beginning \
    --max-messages 5 --timeout-ms 60000 2>/dev/null | grep -c '"n"')
  [ "$got" -eq 5 ] || fail "group-mode consume returned $got of 5 messages"
  pass "produced and consumed 5 messages through a consumer group"
}

smoke_flink() {
  retry 40 5 http_ok "http://127.0.0.1:8082/config" || fail "JobManager REST never answered"
  local out
  out=$(docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1 <<'SQL'
CREATE CATALOG ice WITH ('type'='iceberg','catalog-type'='rest','uri'='http://catalog:8181','warehouse'='s3://warehouse','s3.endpoint'='http://seaweed:8333','s3.path-style-access'='true','s3.access-key-id'='user','s3.secret-access-key'='password');
SHOW CATALOGS;
SQL
)
  grep -q "ice" <<<"$out" || { echo "$out" | tail -20; fail "Iceberg catalog did not register (connector factory or Hadoop classes missing)"; }
  # The image ships --add-opens in config.yaml; mounting a replacement wipes them
  # and Kryo then fails on java.nio buffers at checkpoint time.
  docker exec flink-jobmanager sh -c 'ps ax | grep -q "add-opens=java.base/java.nio"' \
    || fail "JVM module flags missing from the TaskManager command line"
  pass "Iceberg catalog registered and JVM module flags present"
}

smoke_spark() {
  local out
  out=$(docker exec spark-master /opt/spark/bin/spark-sql -e "
    CREATE NAMESPACE IF NOT EXISTS iceberg.smoke;
    CREATE OR REPLACE TABLE iceberg.smoke.t (id BIGINT) USING iceberg;
    INSERT INTO iceberg.smoke.t VALUES (1),(2),(3);
    SELECT count(*) FROM iceberg.smoke.t;" 2>&1)
  grep -qE "^3$" <<<"$out" || { echo "$out" | tail -20; fail "spark-sql could not round-trip an Iceberg table"; }
  docker exec spark-master sh -c 'ls /tmp/spark-events | head -1' >/dev/null 2>&1 \
    || fail "no event log written, so the event log directory is not writable"
  pass "spark-sql wrote and read an Iceberg table, event logging works"
}

smoke_ch_lite() {
  retry 30 5 docker exec ch-11 clickhouse-client --password password -q "SELECT 1" \
    || fail "ch-11 never answered"
  # Databases come from /docker-entrypoint-initdb.d on every fresh server.
  ch ch-11 "SHOW DATABASES" | grep -q feature_store || fail "feature_store database missing"
  ch ch-11 "DROP TABLE IF EXISTS default.smoke" >/dev/null
  ch ch-11 "CREATE TABLE default.smoke (id UInt32) ENGINE=MergeTree ORDER BY id" >/dev/null
  ch ch-11 "INSERT INTO default.smoke SELECT number FROM numbers(10)" >/dev/null
  [ "$(ch ch-11 "SELECT count() FROM default.smoke")" = "10" ] || fail "MergeTree round trip failed"
  pass "databases initialised and MergeTree round trip works"
}

smoke_ch_full() {
  retry 30 5 docker exec ch-21 clickhouse-client --password password -q "SELECT 1" \
    || fail "ch-21 never answered"
  # Exercises keeper and the dual-stack listeners: replicated DDL fails with
  # "Connection refused" when keeper listens on IPv4 only.
  ch ch-11 "DROP TABLE IF EXISTS default.repl ON CLUSTER '{cluster}' SYNC" >/dev/null 2>&1
  ch ch-11 "CREATE TABLE default.repl ON CLUSTER '{cluster}' (id UInt32) ENGINE=ReplicatedMergeTree ORDER BY id" >/dev/null \
    || fail "replicated DDL failed, check keeper reachability"
  ch ch-11 "INSERT INTO default.repl SELECT number FROM numbers(50)" >/dev/null
  retry 12 5 bash -c '[ "$(docker exec ch-12 clickhouse-client --password password -q "SELECT count() FROM default.repl" 2>/dev/null)" = "50" ]' \
    || fail "rows never replicated to the sibling replica"
  [ "$(ch ch-21 "SELECT count() FROM default.repl")" = "0" ] || fail "shard 2 unexpectedly holds shard 1 data"
  pass "replicated table converged on shard 1 and stayed off shard 2"
}

# Catalog registration finishes after the health endpoint starts answering, so
# poll rather than asserting once. Catalogs load even when their backing service
# is absent, which is why this can be required in a trino-only profile group.
catalogs_loaded() {
  local cat
  cat=$(docker exec trino trino --execute "SHOW CATALOGS" 2>/dev/null | tr -d '"')
  for expected in iceberg kafka clickhouse postgres; do
    grep -q "^${expected}$" <<<"$cat" || return 1
  done
}

smoke_trino() {
  retry 40 5 http_ok "http://127.0.0.1:8080/v1/info" || fail "Trino never answered"
  retry 24 5 catalogs_loaded || {
    docker exec trino trino --execute "SHOW CATALOGS" 2>&1 | tail -10
    fail "not every catalog loaded within two minutes"
  }
  docker exec trino trino --execute "SELECT 1" >/dev/null 2>&1 || fail "query execution failed"
  pass "all catalogs loaded and a query ran"
}

smoke_infra() {
  case "$PROFILE" in
    postgres)
      retry 30 5 docker exec postgres pg_isready -U user || fail "postgres never became ready"
      docker exec postgres psql -U user -d odctl -c "SELECT 1" >/dev/null 2>&1 || fail "psql query failed"
      pass "accepting connections and running queries" ;;
    storage)
      retry 30 5 http_reachable "http://127.0.0.1:8333" || fail "S3 API never answered"
      pass "S3 API reachable" ;;
    catalog)
      retry 30 5 http_ok "http://127.0.0.1:8181/v1/config" || fail "REST catalog never answered"
      curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{"namespace":["smoke"]}' "http://127.0.0.1:8181/v1/namespaces" >/dev/null 2>&1
      curl -fsS "http://127.0.0.1:8181/v1/namespaces" 2>/dev/null | grep -q smoke \
        || fail "namespace create or list failed"
      pass "namespace created and listed through the REST API" ;;
    valkey)
      local vk="redis://user:password@localhost:6379"
      retry 30 5 docker exec valkey valkey-cli -u "$vk" ping \
        || fail "valkey never answered PING"
      # product-recommender writes LinUCB models as a multi-key write and reads
      # them back with a batch MGET, so assert that round trip rather than a ping.
      docker exec valkey valkey-cli -u "$vk" \
        mset 'linucb:smoke-1' '{"a":1}' 'linucb:smoke-2' '{"a":2}' >/dev/null 2>&1 \
        || fail "multi-key MSET failed"
      local got
      got=$(docker exec valkey valkey-cli -u "$vk" mget 'linucb:smoke-1' 'linucb:smoke-2' 2>/dev/null | grep -c '"a"')
      [ "$got" -eq 2 ] || fail "batch MGET returned $got of 2 values, expected 2"
      docker exec valkey valkey-cli -u "$vk" del 'linucb:smoke-1' 'linucb:smoke-2' >/dev/null 2>&1
      pass "authenticated, multi-key write and batch MGET round-tripped" ;;
  esac
}

# A profile with no functional assertion yet still has to expose its endpoint.
smoke_http_only() {
  local url="$1"
  retry 60 5 http_ok "$url" || fail "no HTTP response from $url"
  pass "HTTP endpoint answering at $url"
}

case "$PROFILE" in
  kafka-lite)            smoke_kafka kafka ;;
  kafka-full)            smoke_kafka kafka-1 ;;
  flink-lite|flink-full) smoke_flink ;;
  spark-lite|spark-full) smoke_spark ;;
  ch-lite)               smoke_ch_lite ;;
  ch-full)               smoke_ch_full ;;
  trino)                 smoke_trino ;;
  postgres|storage|catalog|valkey) smoke_infra ;;
  metabase)   smoke_http_only "http://127.0.0.1:3000/api/health" ;;
  airflow)    smoke_http_only "http://127.0.0.1:8085/api/v2/monitor/health" ;;
  mlflow)     smoke_http_only "http://127.0.0.1:5000/health" ;;
  ray-serve)  smoke_http_only "http://127.0.0.1:8265" ;;
  lineage)    smoke_http_only "http://127.0.0.1:5002/api/v1/namespaces" ;;
  telemetry)  smoke_http_only "http://127.0.0.1:19090/-/ready" ;;
  metadata)   smoke_http_only "http://127.0.0.1:8585/api/v1/system/version" ;;
  fluss)
    retry 40 5 bash -c 'docker ps --format "{{.Names}}" | grep -q fluss-coordinator' \
      || fail "coordinator container never appeared"
    # Present is not the same as stable: a restart loop keeps the name in
    # docker ps while the service never stays up. No consumer drives Fluss yet,
    # so not failing is the whole bar.
    for c in fluss-coordinator fluss-tablet-1; do
      docker ps --format '{{.Names}}' | grep -q "$c" || continue
      restarts=$(docker inspect -f '{{.RestartCount}}' "$c" 2>/dev/null || echo 0)
      [ "${restarts:-0}" -eq 0 ] || fail "$c restarted $restarts times"
    done
    pass "coordinator and tablet server running without restarts" ;;
  *)
    echo "ℹ️  $PROFILE: no functional assertion defined, checking containers only"
    [ "$(docker ps -q | wc -l)" -ge 1 ] || fail "no containers running"
    pass "containers running" ;;
esac
