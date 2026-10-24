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
MB_USER="smoke@example.com"
MB_PASS="Smoke-test-1234"

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
# retry() throws stdout away, which a value-returning probe needs to keep.
retry_out() {
  local tries="$1" delay="$2"; shift 2
  local out
  for ((i = 1; i <= tries; i++)); do
    if out=$("$@" 2>/dev/null) && [ -n "$out" ]; then printf '%s' "$out"; return 0; fi
    sleep "$delay"
  done
  return 1
}


# Some endpoints answer 403 or 404 to an unauthenticated probe, which still
# proves the service is listening.
http_reachable() {
  local code
  code=$(curl -s -o /dev/null --max-time 10 -w '%{http_code}' "$1")
  [ -n "$code" ] && [ "$code" != "000" ]
}

ch() { docker exec "$1" clickhouse-client --password password -q "$2" 2>&1; }

# Guide commands live in docs/snippets/<guide>/, one section per step, and each
# guide page shows a copy of its sections, which tests/test_docs.py compares.
# Running the same sections here proves the commands on the page work.
SNIPPETS="$(cd "$(dirname "$0")/../.." && pwd)/docs/snippets"

# Print one section of a snippet file: snippet kafka/commands.sh create-topic
snippet() {
  awk -v s="$2" 'index($0, "--8<-- [start:" s "]") {on = 1; next}
    index($0, "--8<-- [end:" s "]") {on = 0} on' "$SNIPPETS/$1"
}

# Run a bash section from the current directory, where the reader's .odctl
# workspace is, so an `odctl up` in a step reads the workspace's .env.
run_snippet() {
  local file="$1" section="$2" code
  code=$(snippet "$file" "$section")
  [ -n "$code" ] || fail "no section $section in docs/snippets/$file"
  bash -o pipefail -c "$code"
}

# Run a section and check its output: snippet_says kafka/commands.sh list -F 'orders'.
# The whole output is read before grep looks at it. A grep -q at the end of a pipe
# stops at the first match, the command then fails writing its next line, and
# pipefail reports the check as failed.
snippet_says() {
  local file="$1" section="$2" out
  shift 2
  out=$(run_snippet "$file" "$section" 2>/dev/null) || return 1
  grep -q "$@" <<<"$out"
}

# Run a guide's Runnable Example from the current directory, where the .odctl
# workspace is, and check that its output matches an extended regular
# expression: run_example kafka '"n":5'. The optional third argument is the
# command that runs the file, such as a Python with the client installed.
run_example() {
  local guide="$1" want="$2" runner="${3:-bash}" file out
  file=$(ls "$SNIPPETS/$guide"/example.* 2>/dev/null | head -1)
  [ -n "$file" ] || fail "no runnable example in docs/snippets/$guide"
  out=$($runner "$file" 2>&1) || { echo "$out" | tail -20; fail "the $guide example failed"; }
  grep -qE -- "$want" <<<"$out" || { echo "$out" | tail -20; fail "the $guide example printed no '$want'"; }
  pass "the $guide guide's runnable example printed '$want'"
}

# The commands that run the MLflow and Evidently examples: a Python 3.12 with
# the client versions the images pin, as the guides tell the reader to install.
mlflow_runner() {
  local dockerfile="$SNIPPETS/../../src/odctl/resources/docker/mlflow/Dockerfile" mlflow xgboost
  mlflow=$(grep -oE 'mlflow/mlflow:v[0-9.]+' "$dockerfile" | head -1 | cut -dv -f2)
  xgboost=$(grep -oE "xgboost~=[0-9.]+" "$dockerfile" | head -1 | cut -d= -f2)
  echo "uv run --no-project --quiet --python 3.12 --with mlflow==$mlflow --with xgboost~=$xgboost"
}
evidently_runner() {
  local version
  version=$(grep -oE 'evidently/evidently-service:[0-9.]+' \
    "$SNIPPETS/../../src/odctl/resources/compose-mlops.yml" | head -1 | cut -d: -f2)
  echo "uv run --no-project --quiet --python 3.12 --with evidently==$version --with pandas<3.1 python"
}

# How It Works edits a workspace file and applies it with odctl recreate. Each
# check runs the guide's section, puts the file back and recreates again, so
# later profiles in the same job see the shipped settings, and matches the
# output against an extended regular expression.
how_it_works_edit() {
  local section="$1" file="$2" profile="$3" want="$4" out
  out=$(run_snippet how-it-works/commands.sh "$section" 2>&1) || { echo "$out" | tail -20; fail "the $section example failed"; }
  mv "$file.bak" "$file" || fail "the $section example left no $file.bak"
  odctl recreate "$profile" >/dev/null 2>&1 || fail "could not recreate $profile after the $section example"
  grep -qE -- "$want" <<<"$out" || { echo "$out" | tail -20; fail "the $section example printed no '$want'"; }
  pass "How It Works' $section example printed '$want'"
}
how_it_works_trino() {
  how_it_works_edit trino-port .odctl/compose-analytics.yml trino '8080/tcp -> 127\.0\.0\.1:8180'
  retry 30 5 http_ok "http://127.0.0.1:8080/v1/info" || fail "Trino did not answer on 8080 after the port was put back"
}
how_it_works_airflow() {
  how_it_works_edit airflow-deps .odctl/.env airflow '^1\.4\.3$'
}

# Metrics: nothing else here reads a metrics endpoint, so a change that breaks
# one goes unseen. In 0.8.0 the JMX agent in KAFKA_OPTS broke every Kafka CLI
# run, and only an unrelated topic check caught it. So each profile reads its
# scrape targets the way Prometheus does, by name on the odctl network, from a
# throwaway alpine container, since most targets publish no port and some images
# have no HTTP client. Any wget options go before the URL.
metrics_ok() {
  local out
  out=$(docker run --rm --network odctl alpine wget -qO- -T 10 "$@" 2>/dev/null) || return 1
  # A sample line, not a # TYPE line: Spark's servlet writes samples only.
  grep -qE '^[a-zA-Z_:][a-zA-Z0-9_:]*(\{.*\})? [-+0-9.eEInfNa]+' <<<"$out"
}

# Retried, because a metrics reporter can start after the port a profile waits on.
assert_metrics() {
  local url
  for url in "$@"; do
    retry 12 5 metrics_ok "$url" || fail "no Prometheus samples at $url"
  done
  pass "Prometheus samples at$(printf ' %s' "$@")"
}

# Push and collector sources have no endpoint to read. When the telemetry
# profile is up, their series must reach its Prometheus; when it is not, nothing
# receives them, so there is nothing to assert.
prom_has() {
  curl -fsS --max-time 10 -G "http://127.0.0.1:19090/api/v1/query" \
    --data-urlencode "query=count({__name__=~\"$1\"})" 2>/dev/null \
    | python3 -c 'import json, sys; sys.exit(0 if json.load(sys.stdin)["data"]["result"] else 1)'
}

assert_pushed_metrics() {
  local match="$1" what="$2"
  if ! docker ps --format '{{.Names}}' | grep -qx otel-lgtm; then
    echo "ℹ️  $PROFILE: telemetry is not up, so $what metrics are not checked"
    return 0
  fi
  retry 12 10 prom_has "$match" || fail "no $what series ($match) in Prometheus"
  pass "$what series ($match) in Prometheus"
}

kafka_topic() {
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 "$@"
}

# kafka-lite runs the guide's commands. kafka-full keeps smoke_kafka below,
# because its broker container is kafka-1, not the kafka the guide names.
guide_kafka() {
  local out
  retry 30 5 docker exec kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server broker-1:19092 --list || fail "broker never became reachable"
  run_snippet kafka/commands.sh create-topic >/dev/null 2>&1 || fail "could not create the topic"
  # The consumer reads through a group on purpose. Assign mode bypasses the
  # coordinator and would pass even when __consumer_offsets cannot be created.
  local got
  got=$(run_snippet kafka/commands.sh produce-consume 2>/dev/null | grep -c '"n"')
  [ "$got" -eq 5 ] || fail "group-mode consume returned $got of 5 messages"
  pass "produced and consumed 5 messages through a consumer group"

  # demo was created without settings, so it shows the broker defaults.
  out=$(run_snippet kafka/commands.sh retention-default 2>/dev/null)
  grep -Eq '^ *retention\.ms=86400000 ' <<<"$out" && grep -Eq '^ *retention\.bytes=524288000 ' <<<"$out" \
    || { echo "$out"; fail "a topic created without settings did not get one day and 500 MB"; }
  pass "the broker defaults are one day and 500 MB per partition"
  kafka_topic --delete --topic history >/dev/null 2>&1
  out=$(run_snippet kafka/commands.sh retention-unlimited 2>/dev/null)
  grep -q 'retention.ms=-1' <<<"$out" && grep -q 'retention.bytes=-1' <<<"$out" \
    || { echo "$out"; fail "the topic did not take retention.ms=-1 and retention.bytes=-1"; }
  pass "a topic created with retention.ms and retention.bytes at -1 keeps both"
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

# The plugins come from the deps volume, so a missing or misnamed folder only
# shows up here: Connect starts and simply does not list the class.
connect_plugins() {
  retry 40 5 http_ok "http://127.0.0.1:8083/connector-plugins" || fail "Connect REST never answered"
  local plugins
  plugins=$(run_snippet kafka-connect/commands.sh plugins 2>/dev/null)
  for cls in org.apache.iceberg.connect.IcebergSinkConnector \
    io.debezium.connector.postgresql.PostgresConnector \
    com.clickhouse.kafka.connect.ClickHouseSinkConnector; do
    grep -q "$cls" <<<"$plugins" || fail "Connect does not list $cls"
  done
  pass "Connect lists the Iceberg, Debezium and ClickHouse plugins"
}

# The Kafka Connect guide registers the MSK data generator, which needs only
# Kafka, reads three of its records, then checks and removes the connector.
connect_datagen() {
  (cd "$SNIPPETS/kafka-connect" && run_snippet kafka-connect/commands.sh register) >/dev/null 2>&1 \
    || fail "Connect rejected the data generator configuration"
  local got status
  got=$(run_snippet kafka-connect/commands.sh read 2>/dev/null | grep -c '"name"')
  [ "$got" -eq 3 ] || fail "read $got of 3 data generator records from customers"
  retry 12 5 sh -c "curl -fsS http://127.0.0.1:8083/connectors/demo-datagen/status | grep -q '\"state\":\"RUNNING\"'" \
    || fail "the data generator was not RUNNING"
  status=$(run_snippet kafka-connect/commands.sh status-remove 2>/dev/null)
  grep -q '"state":"RUNNING"' <<<"$status" || { echo "$status"; fail "the data generator status was not RUNNING"; }
  curl -fsS "http://127.0.0.1:8083/connectors/demo-datagen" >/dev/null 2>&1 \
    && fail "the data generator is still registered after the delete"
  pass "the data generator wrote records to customers, and was checked and removed"
}

# Getting Started runs each read-only command on kafka-lite, then restarts it.
getting_started() {
  local out
  out=$(run_snippet getting-started/commands.sh list 2>&1) || fail "odctl list failed"
  grep -q "kafka-lite" <<<"$out" || fail "odctl list does not name kafka-lite"
  out=$(run_snippet getting-started/commands.sh list-details 2>&1) || fail "odctl list -d failed"
  grep -q "kafka-ui" <<<"$out" || fail "odctl list -d does not name the kafka-ui service"
  out=$(run_snippet getting-started/commands.sh explain 2>&1) || fail "odctl explain failed"
  grep -q "karapace" <<<"$out" || fail "odctl explain kafka-lite does not name karapace"
  out=$(run_snippet getting-started/commands.sh info 2>&1) || fail "odctl info failed"
  grep -q "Reachable" <<<"$out" || fail "odctl info does not say Docker is reachable"
  out=$(run_snippet getting-started/commands.sh ps 2>&1) || fail "odctl ps failed"
  grep -q "connect" <<<"$out" || fail "odctl ps kafka-lite does not list connect"
  out=$(run_snippet getting-started/commands.sh ps-all 2>&1) || fail "odctl ps --all failed"
  grep -q "karapace" <<<"$out" || fail "odctl ps --all does not list karapace"
  out=$(run_snippet getting-started/commands.sh logs 2>&1) || fail "odctl logs failed"
  grep -q "^connect" <<<"$out" || fail "odctl logs printed no connect lines"
  out=$(run_snippet getting-started/commands.sh logs-time 2>&1) || fail "odctl logs with --since and --until failed"
  grep -qE "^connect +\| [0-9]{4}-" <<<"$out" || fail "odctl logs -t printed no timestamped connect lines: $out"
  out=$(run_snippet getting-started/commands.sh down-dry-run 2>&1) || fail "odctl down --dry-run failed"
  docker inspect connect >/dev/null 2>&1 || fail "odctl down --dry-run removed a container"
  out=$(run_snippet getting-started/commands.sh restart 2>&1) || fail "odctl restart failed"
  grep -q "Restart complete" <<<"$out" || fail "odctl restart did not complete"
  retry 40 5 http_ok "http://127.0.0.1:8083/connectors" || fail "Connect never answered after the restart"
  pass "Getting Started's list, explain, info, ps, logs, restart and down --dry-run ran on kafka-lite"
}

# The Iceberg sink is built from source, so prove it commits a snapshot rather
# than only loading. It needs the catalog, which kafka-lite does not start.
smoke_iceberg_sink() {
  odctl up catalog >/dev/null 2>&1 || fail "could not start the catalog for the Iceberg sink"
  retry 30 5 http_ok "http://127.0.0.1:8181/v1/config" || fail "REST catalog never answered"
  run_snippet iceberg-ingestion/commands.sh create-table >/dev/null 2>&1 \
    || fail "could not create the sink's target table"
  run_snippet iceberg-ingestion/commands.sh topics-produce >/dev/null 2>&1 \
    || fail "could not create the topics or produce to demo-iceberg"
  # From the snippet folder, where the guide's @demo-iceberg.json is.
  (cd "$SNIPPETS/iceberg-ingestion" && run_snippet iceberg-ingestion/commands.sh register) >/dev/null 2>&1 \
    || fail "Connect rejected the Iceberg sink configuration"

  # The first commit waits for the control consumer to join its group, which
  # takes a minute or more on a fresh worker.
  local api="http://127.0.0.1:8181/v1/namespaces" records=""
  for _ in $(seq 1 60); do
    records=$(curl -fsS "$api/demo/tables/kc" 2>/dev/null | python3 -c '
import json, sys
m = json.load(sys.stdin)["metadata"]
cur = m.get("current-snapshot-id")
snap = [s for s in m.get("snapshots", []) if s["snapshot-id"] == cur]
print(snap[0]["summary"].get("total-records", "") if snap else "")' 2>/dev/null)
    [ "$records" = "5" ] && break
    sleep 5
  done
  if [ "$records" != "5" ]; then
    run_snippet kafka-connect/commands.sh logs 2>&1
    fail "the Iceberg sink committed ${records:-no} records, expected 5"
  fi
  run_snippet kafka-connect/commands.sh logs >/dev/null 2>&1 || fail "could not read the Connect log"
  local status
  snippet_says iceberg-ingestion/commands.sh records -F '"total-records":"5"' \
    || fail "the guide's records step does not show 5 records"
  status=$(run_snippet iceberg-ingestion/commands.sh status-remove 2>/dev/null)
  grep -q '"state":"RUNNING"' <<<"$status" || { echo "$status"; fail "the connector status was not RUNNING"; }
  curl -fsS "http://127.0.0.1:8083/connectors/demo-iceberg" >/dev/null 2>&1 \
    && fail "the connector is still registered after the delete"
  pass "the Iceberg sink committed 5 records to an Iceberg table, and was checked and removed"
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

  # Registering the catalog loads the runtime jar but writes nothing. The Ingest
  # into Iceberg guide's batch insert and read proves the runtime, the Hadoop
  # classes and S3FileIO work together on this Flink minor.
  out=$(snippet iceberg-ingestion/steps.sql flink \
    | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  grep -qE "^\| +3 \|$" <<<"$out" || { echo "$out" | tail -30; fail "Flink could not write and read an Iceberg table"; }
  pass "Flink wrote 3 rows to an Iceberg table and read them back"
}

# Right after kafka-lite starts, Karapace answers its health check but times out
# on a schema write until its producer reaches the broker. Wait for a write.
wait_karapace_write() {
  retry 24 5 curl -fsS --max-time 10 -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
    -d '{"schema": "{\"type\":\"string\"}"}' http://127.0.0.1:8081/subjects/smoke-ready/versions \
    >/dev/null 2>&1 || fail "Karapace never accepted a schema"
}

# The Kafka, Avro with schema registry, and JDBC jars come from the deps image
# and must match the Flink minor. Write Avro to Kafka through Karapace, read it
# back, and write an aggregate to PostgreSQL over JDBC. flink-lite already starts
# PostgreSQL through the catalog; Kafka is started here.
smoke_flink_kafka_jdbc() {
  odctl up kafka-lite >/dev/null 2>&1 || fail "could not start kafka-lite for the Flink Kafka and JDBC check"
  retry 30 5 kafka_topic --list >/dev/null 2>&1 || fail "broker never became reachable"
  wait_karapace_write
  run_snippet flink-sql/commands.sh create-topic-table >/dev/null 2>&1 \
    || fail "could not create the topic or the JDBC target table"
  local out
  out=$(snippet flink-sql/steps.sql kafka-to-postgres \
    | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  run_snippet flink-sql/commands.sh check >/dev/null 2>&1 || fail "the guide's check query failed"
  local rows
  rows=$(docker exec postgres psql -U user -d odctl -tAc \
    "SELECT string_agg(supplier || '=' || orders || '/' || total, ',' ORDER BY supplier) FROM supplier_stats" 2>/dev/null)
  [ "$rows" = "a=2/15,b=1/7.5" ] || { echo "$out" | grep -iE "error|exception" | tail -10; fail "Kafka Avro to JDBC through Flink SQL gave '$rows', expected a=2/15,b=1/7.5"; }
  pass "Flink read Avro from Kafka through the schema registry and wrote an aggregate to PostgreSQL over JDBC"

  # Two different OVER windows in one streaming query are refused, so the guide
  # runs one statement for each window size, each writing its own table.
  local refused
  refused=$(snippet rolling-windows/steps.sql windows-refused | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  grep -qF '[ERROR]' <<<"$refused" || fail "Flink did not refuse two different OVER windows: $(tail -5 <<<"$refused")"
  run_snippet rolling-windows/commands.sh create-window-tables >/dev/null 2>&1 || fail "could not create the window tables"
  out=$(snippet rolling-windows/steps.sql windows-one-per-size | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  run_snippet rolling-windows/commands.sh check-windows >/dev/null 2>&1 || fail "the guide's window check query failed"
  rows=$(docker exec postgres psql -U user -d odctl -tAc \
    "SELECT (SELECT count(*) FROM card_sum_10m) || ',' || (SELECT count(*) FROM card_sum_1h)" 2>/dev/null)
  [ "$rows" = "20,20" ] || { echo "$out" | grep -iE "error|exception" | tail -10; fail "one statement for each OVER window gave '$rows' rows, expected 20,20"; }
  pass "Flink refused two different OVER windows and one statement for each window size wrote its own table"
}

# The HTTP jar comes from the deps image. Push a feature value to Feast's /push
# through the HTTP sink and read it back. The Flink job finishes even when Feast
# rejects the request, so the read-back is the only proof. Feast caches its
# registry for up to a minute after apply, and the read uses that cache too.
smoke_flink_http() {
  odctl up feast >/dev/null 2>&1 || fail "could not start feast for the Flink HTTP check"
  retry 40 5 http_ok "http://127.0.0.1:6566/health" || fail "Feast never answered on :6566"
  (cd "$SNIPPETS/feast-iceberg" && run_snippet feast-iceberg/commands.sh push-apply) >/dev/null 2>&1 \
    || fail "could not apply the Feast push source"
  local out
  out=$(snippet feast-iceberg/steps.sql feast-push | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  feast_value() { run_snippet feast-iceberg/commands.sh push-read 2>/dev/null | grep -F 0.8999999761581421; }
  retry 24 5 feast_value \
    || { echo "$out" | grep -iE "error|exception" | tail -10; fail "Feast never returned the value the Flink HTTP sink pushed"; }
  odctl down feast >/dev/null 2>&1 || fail "could not stop feast after the Flink HTTP check"
  pass "Flink sent a row to Feast's /push through the HTTP sink and the value came back"
}

smoke_spark() {
  local out
  out=$(run_snippet spark/commands.sh run-sql 2>&1)
  grep -qE "^3$" <<<"$out" || { echo "$out" | tail -20; fail "spark-sql could not round-trip an Iceberg table"; }
  out=$(run_snippet spark/commands.sh event-logs 2>/dev/null)
  [ -n "$out" ] || fail "no event log written, so the event log directory is not writable"
  pass "spark-sql wrote and read an Iceberg table, event logging works"

  # The Kafka connector and its dependencies come from the deps image, so the
  # job runs with no --packages option. kafka-lite is started here.
  odctl up kafka-lite >/dev/null 2>&1 || fail "could not start kafka-lite for the Spark Kafka check"
  retry 30 5 kafka_topic --list >/dev/null 2>&1 || fail "broker never became reachable"
  kafka_topic --delete --topic spark-demo >/dev/null 2>&1
  run_snippet spark/commands.sh kafka-topic >/dev/null 2>&1 || fail "could not create and fill the spark-demo topic"
  out=$(cd "$SNIPPETS/spark" && run_snippet spark/commands.sh kafka-read 2>&1)
  for n in 1 2 3; do
    grep -qF "{\"n\":$n}" <<<"$out" || { echo "$out" | grep -iE "error|exception" | tail -10; fail "spark.read.format(kafka) did not return {\"n\":$n}"; }
  done
  pass "Spark read 3 messages from a Kafka topic with no --packages option"

  # Avro records written with the schema registry, as the Flink SQL guide writes
  # the orders topic: the job reads the subject's latest schema from Karapace,
  # drops the 5-byte prefix and decodes the rest.
  wait_karapace_write
  kafka_topic --delete --topic orders >/dev/null 2>&1
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
    --create --topic orders --partitions 1 --replication-factor 1 >/dev/null 2>&1 || fail "could not create the orders topic"
  out=$(docker exec -i karapace python3 - < "$(dirname "$0")/spark_avro_producer.py" 2>&1) || { echo "$out" | tail -10; fail "could not write Avro records to the orders topic"; }
  out=$(cd "$SNIPPETS/spark" && run_snippet spark/commands.sh avro-read 2>&1)
  for row in "a|5.0" "a|10.0" "b|7.5"; do
    grep -qE "^\| *${row%|*} *\| *${row#*|} *\|$" <<<"$out" \
      || { echo "$out" | grep -iE "error|exception" | tail -10; fail "from_avro did not return ${row%|*} ${row#*|}"; }
  done
  pass "Spark decoded 3 Avro records written with the schema registry"
  odctl down kafka-lite >/dev/null 2>&1 || fail "could not stop kafka-lite after the Spark Kafka check"
}

smoke_ch_lite() {
  retry 30 5 docker exec ch-11 clickhouse-client --password password -q "SELECT 1" \
    || fail "ch-11 never answered"
  local out
  out=$(run_snippet clickhouse/commands.sh merge-tree 2>&1)
  # Databases come from /docker-entrypoint-initdb.d on every fresh server.
  grep -qx feature_store <<<"$out" || fail "feature_store database missing"
  [ "$(tail -1 <<<"$out")" = "10" ] || { echo "$out"; fail "MergeTree round trip failed"; }
  pass "databases initialised and MergeTree round trip works"
  assert_metrics http://ch-11:9363/metrics http://ch-12:9363/metrics
}

smoke_ch_full() {
  retry 30 5 docker exec ch-21 clickhouse-client --password password -q "SELECT 1" \
    || fail "ch-21 never answered"
  # Exercises keeper and the dual-stack listeners: replicated DDL fails with
  # "Connection refused" when keeper listens on IPv4 only.
  local out
  out=$(run_snippet clickhouse/commands.sh replicated 2>&1) \
    || { echo "$out" | tail -20; fail "replicated DDL failed, check keeper reachability"; }
  # The guide reads ch-12 at once; replication can take a moment, so wait here.
  retry 12 5 bash -c '[ "$(docker exec ch-12 clickhouse-client --password password -q "SELECT count() FROM default.repl" 2>/dev/null)" = "50" ]' \
    || fail "rows never replicated to the sibling replica"
  [ "$(ch ch-21 "SELECT count() FROM default.repl")" = "0" ] || fail "shard 2 unexpectedly holds shard 1 data"
  pass "replicated table converged on shard 1 and stayed off shard 2"
  assert_metrics http://ch-11:9363/metrics http://ch-12:9363/metrics \
    http://ch-21:9363/metrics http://ch-22:9363/metrics
}

# Catalog registration finishes after the health endpoint starts answering, so
# poll rather than asserting once. Catalogs load even when their backing service
# is absent, which is why this can be required in a trino-only profile group.
catalogs_loaded() {
  local cat
  cat=$(run_snippet trino-metabase/commands.sh catalogs 2>/dev/null | tr -d '"')
  for expected in iceberg kafka clickhouse postgres; do
    grep -q "^${expected}$" <<<"$cat" || return 1
  done
}

smoke_trino() {
  retry 40 5 http_ok "http://127.0.0.1:8080/v1/info" || fail "Trino never answered"
  retry 24 5 catalogs_loaded || {
    run_snippet trino-metabase/commands.sh catalogs 2>&1 | tail -10
    fail "not every catalog loaded within two minutes"
  }
  [ "$(run_snippet trino-metabase/commands.sh query 2>/dev/null | tr -d '"')" = "1" ] || fail "query execution failed"
  pass "all catalogs loaded and a query ran"
  # As Prometheus logs in: user prometheus with no password, which rules.json
  # allows to read system information.
  retry 12 5 metrics_ok --header "Authorization: Basic $(printf 'prometheus:' | base64)" \
    http://trino:8080/metrics || fail "no Prometheus samples at http://trino:8080/metrics"
  pass "Prometheus samples at http://trino:8080/metrics"
}

smoke_infra() {
  case "$PROFILE" in
    postgres)
      retry 30 5 docker exec postgres pg_isready -U user || fail "postgres never became ready"
      docker exec postgres psql -U user -d odctl -c "SELECT 1" >/dev/null 2>&1 || fail "psql query failed"
      pass "accepting connections and running queries"
      # odctl's image adds pgvector, pg_textsearch and PostGIS, and
      # 01-init-databases.sh creates them in a `vector` database. SELECT 1 on
      # `odctl` proves none of that, so run the hybrid search guide's SQL there.
      local nearest
      nearest=$(snippet hybrid-search/steps.sql vector \
        | docker exec -i postgres psql -U user -d vector -v ON_ERROR_STOP=1 -tAq 2>/dev/null | tr -d '[:space:]')
      [ "$nearest" = "1" ] || fail "pgvector similarity returned row '$nearest', expected 1"
      pass "pgvector: vector column, HNSW index and similarity ordering all work"
      # pg_textsearch only works when preloaded, so a BM25 index proves the
      # shared_preload_libraries setting as well as the extension. Its index
      # build reports NOTICE lines on stderr, which are left out.
      local bm25
      bm25=$(snippet hybrid-search/steps.sql bm25 \
        | docker exec -i postgres psql -U user -d vector -v ON_ERROR_STOP=1 -tAq 2>/dev/null | tr -d '[:space:]')
      [ "$bm25" = "2" ] || fail "pg_textsearch BM25 query returned '$bm25', expected 2"
      pass "pg_textsearch: BM25 index and ranking work"
      local metres
      metres=$(docker exec postgres psql -U user -d vector -tAc \
        "SELECT round(ST_Distance('POINT(151.2093 -33.8688)'::geography, 'POINT(144.9631 -37.8136)'::geography) / 1000)" \
        2>&1 | tr -d '[:space:]')
      # Sydney to Melbourne is about 714 km on the spheroid.
      [ "$metres" = "714" ] || fail "PostGIS distance returned '$metres' km, expected 714"
      pass "PostGIS: geography distance works"
      # Read by the telemetry collector's postgresql receiver.
      assert_pushed_metrics 'postgresql_.+' PostgreSQL
      run_example hybrid-search '^ +2$' ;;
    storage)
      retry 30 5 http_reachable "http://127.0.0.1:8333" || fail "S3 API never answered"
      # A port that answers is not a bucket that stores anything. Spark, Flink,
      # Iceberg and Airflow's DAG bundle all use it, so assert the round
      # trip. Signed, because the S3 API refuses anonymous requests with 403,
      # which also makes this a check on the credentials the whole stack uses.
      local s3="http://localhost:8333/warehouse/odctl-smoke-$$.txt"
      local sig='--aws-sigv4 aws:amz:us-east-1:s3 --user'
      local cred="${AWS_ACCESS_KEY_ID:-user}:${AWS_SECRET_ACCESS_KEY:-password}"
      docker exec seaweed sh -c "echo odctl-smoke > /tmp/odctl-smoke.txt" >/dev/null 2>&1
      docker exec seaweed sh -c \
        "curl -fsS $sig '$cred' -X PUT --data-binary @/tmp/odctl-smoke.txt '$s3'" \
        >/dev/null 2>&1 || fail "could not write an object to $s3"
      local body
      body=$(docker exec seaweed sh -c "curl -fsS $sig '$cred' '$s3'" 2>/dev/null | tr -d '[:space:]')
      docker exec seaweed sh -c "curl -fsS $sig '$cred' -X DELETE '$s3'" >/dev/null 2>&1 || true
      [ "$body" = "odctl-smoke" ] || fail "read back '$body' from S3, expected odctl-smoke"
      pass "signed write, read back and delete through the S3 API"
      # A model of a few hundred MB uploaded three times in a row. Without
      # GOMEMLIMIT, SeaweedFS grew to its 512 MB limit and the kernel killed it
      # during the second or third upload, with HTTP 500 for the client.
      local big="http://localhost:8333/warehouse/odctl-big-$$.bin" n
      docker exec seaweed sh -c "head -c 267832560 /dev/urandom > /tmp/odctl-big.bin" >/dev/null 2>&1 \
        || fail "could not create a 268 MB file in the seaweed container"
      for n in 1 2 3; do
        docker exec seaweed sh -c \
          "curl -fsS $sig '$cred' -X PUT --data-binary @/tmp/odctl-big.bin '$big'" >/dev/null 2>&1 \
          || fail "upload $n of 3 of a 268 MB file failed; seaweed OOMKilled=$(docker inspect -f '{{.State.OOMKilled}}' seaweed 2>&1)"
      done
      [ "$(docker inspect -f '{{.State.OOMKilled}} {{.State.Running}}' seaweed)" = "false true" ] \
        || fail "seaweed was killed or stopped during the large uploads"
      docker exec seaweed sh -c "curl -fsS $sig '$cred' -X DELETE '$big'; rm -f /tmp/odctl-big.bin" >/dev/null 2>&1 || true
      pass "three uploads of 268 MB passed and seaweed was not killed"
      # How it works shows how to create a bucket before its profile exists.
      local buckets
      buckets=$(run_snippet how-it-works/commands.sh create-bucket 2>&1) || fail "the create-bucket example failed: $buckets"
      grep -q "'desflow'" <<<"$buckets" || fail "the bucket list has no desflow: $buckets"
      docker exec seaweed sh -c "curl -fsS $sig '$cred' -X DELETE 'http://localhost:8333/desflow'" >/dev/null 2>&1 || true
      pass "the create-bucket example created a bucket with the S3 login"
      how_it_works_edit seaweed-memory .odctl/compose-infra.yml storage '^2147483648$'
      assert_metrics http://seaweed:9327/metrics ;;
    catalog)
      retry 30 5 http_ok "http://127.0.0.1:8181/v1/config" || fail "REST catalog never answered"
      curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{"namespace":["smoke"]}' "http://127.0.0.1:8181/v1/namespaces" >/dev/null 2>&1
      curl -fsS "http://127.0.0.1:8181/v1/namespaces" 2>/dev/null | grep -q smoke \
        || fail "namespace create or list failed"
      pass "namespace created and listed through the REST API"
      # A namespace is metadata only. Creating a table exercises the JDBC
      # catalog backend and the S3FileIO write that every engine depends on.
      # Drop a table an earlier failed run left behind, or the create gets 409.
      curl -fsS -X DELETE "http://127.0.0.1:8181/v1/namespaces/smoke/tables/t" >/dev/null 2>&1 || true
      curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{"name":"t","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"id","required":true,"type":"long"}]}}' \
        "http://127.0.0.1:8181/v1/namespaces/smoke/tables" >/dev/null 2>&1 \
        || fail "table create failed against the REST catalog"
      curl -fsS "http://127.0.0.1:8181/v1/namespaces/smoke/tables/t" 2>/dev/null \
        | grep -q 'metadata-location' || fail "table metadata did not read back"
      curl -fsS -X DELETE "http://127.0.0.1:8181/v1/namespaces/smoke/tables/t" >/dev/null 2>&1 || true
      pass "table created through the catalog and its metadata read back"
      # How It Works reaches the catalog from a container on the odctl network,
      # previews a start and pulls the catalog's images.
      snippet_says how-it-works/commands.sh reach '"defaults"' \
        || fail "a container on the odctl network did not reach catalog:8181"
      snippet_says how-it-works/commands.sh dry-run 'compose-flink.yml' \
        || fail "odctl up flink-lite --dry-run did not list compose-flink.yml"
      snippet_says how-it-works/commands.sh pull 'All images pulled successfully' \
        || fail "odctl pull catalog did not finish"
      run_snippet how-it-works/commands.sh up-pull >/dev/null 2>&1 || fail "odctl up catalog --pull failed"
      snippet_says how-it-works/commands.sh tag-override 'odctl/postgres:1.1.0' \
        || fail "a TAG in the shell did not change the image odctl explain shows"
      snippet_says how-it-works/commands.sh workspace-flag 'catalog' \
        || fail "odctl --workspace ps catalog listed no catalog container"
      run_snippet how-it-works/commands.sh recreate-pull >/dev/null 2>&1 || fail "odctl recreate catalog --pull failed"
      retry 30 5 http_ok "http://127.0.0.1:8181/v1/config" || fail "REST catalog never answered after the recreate"
      pass "How It Works' reach, dry-run, pull, up --pull, TAG, --workspace and recreate --pull examples ran"
      assert_metrics http://catalog:9404/metrics ;;
    valkey)
      retry 30 5 docker exec valkey valkey-cli --no-auth-warning -u "redis://user:password@localhost:6379" ping \
        || fail "valkey never answered PING"
      # product-recommender writes models as a multi-key write and reads them
      # back with a batch MGET, as the guide does, so assert that round trip.
      local got
      got=$(run_snippet valkey/commands.sh round-trip 2>/dev/null | grep -c '"a"')
      [ "$got" -eq 2 ] || fail "batch MGET returned $got of 2 values, expected 2"
      pass "authenticated, multi-key write and batch MGET round-tripped"
      # Read by the telemetry collector's redis receiver.
      assert_pushed_metrics 'redis_.+' Valkey
      run_example valkey '^\[5\]$' ;;
  esac
}

# Metabase: a bundled driver is not proof it can reach the host. Both clickhouse
# and starburst ship in the image, so the failure mode is the connection, not a
# missing JAR. Metabase sits on the odctl network, so it must use container
# names rather than the published host ports.
mb_session() {
  local props tok sid
  props=$(curl -fsS --max-time 10 http://127.0.0.1:3000/api/session/properties) || return 1
  tok=$(printf '%s' "$props" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("setup-token") or "")')
  if [ -n "$tok" ]; then
    curl -fsS -X POST http://127.0.0.1:3000/api/setup -H 'Content-Type: application/json' \
      -d "{\"token\":\"$tok\",\"user\":{\"first_name\":\"smoke\",\"last_name\":\"test\",\"email\":\"$MB_USER\",\"password\":\"$MB_PASS\",\"site_name\":\"odctl\"},\"prefs\":{\"site_name\":\"odctl\",\"allow_tracking\":false}}" \
      >/dev/null 2>&1
  fi
  sid=$(curl -fsS -X POST http://127.0.0.1:3000/api/session -H 'Content-Type: application/json' \
    -d "{\"username\":\"$MB_USER\",\"password\":\"$MB_PASS\"}" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
  [ -n "$sid" ] && printf '%s' "$sid"
}

# Create a database and run a query through it. Creating one returns 200 even
# when the target is unreachable, so only a completed query proves the path.
mb_query() {
  local sid="$1" name="$2" engine="$3" details="$4" sql="$5" id res
  # Reuse a database of this name if one exists, so a retry does not pile up
  # duplicates against a Metabase whose state outlives the run.
  id=$(curl -fsS http://127.0.0.1:3000/api/database -H "X-Metabase-Session: $sid" 2>/dev/null \
    | MB_NAME="$name" python3 -c 'import json,os,sys
d = json.load(sys.stdin)
for db in (d.get("data") if isinstance(d, dict) else d) or []:
    if db.get("name") == os.environ["MB_NAME"]:
        print(db["id"]); break' 2>/dev/null)
  if [ -z "$id" ]; then
    id=$(curl -fsS -X POST http://127.0.0.1:3000/api/database -H "X-Metabase-Session: $sid" \
      -H 'Content-Type: application/json' \
      -d "{\"name\":\"$name\",\"engine\":\"$engine\",\"details\":$details}" 2>/dev/null \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
  fi
  [ -n "$id" ] || return 1
  res=$(curl -fsS -X POST http://127.0.0.1:3000/api/dataset -H "X-Metabase-Session: $sid" \
    -H 'Content-Type: application/json' \
    -d "{\"database\":$id,\"type\":\"native\",\"native\":{\"query\":\"$sql\"}}" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))' 2>/dev/null)
  [ "$res" = "completed" ]
}

smoke_metabase() {
  local sid
  retry 60 5 http_ok "http://127.0.0.1:3000/api/health" || fail "no HTTP response from :3000"
  snippet_says trino-metabase/commands.sh metabase-health '"status":"ok"' \
    || fail "Metabase health did not report ok"
  assert_metrics http://metabase:9191/metrics
  sid=$(retry_out 12 5 mb_session) || fail "could not obtain a Metabase session"

  # Postgres always: it is Metabase's own application database, so this proves
  # the network path before any analytics engine is involved.
  retry 12 5 mb_query "$sid" pg-smoke postgres \
    '{"host":"postgres","port":5432,"dbname":"metabase","user":"'"${POSTGRES_USER:-user}"'","password":"'"${POSTGRES_PASSWORD:-password}"'"}' \
    'SELECT 1 AS one' || fail "postgres query did not complete"
  pass "queried postgres"

  # ch-11 is in both ch-lite and ch-full, so one connection covers either.
  if docker ps --format '{{.Names}}' | grep -q '^ch-11$'; then
    retry 12 5 mb_query "$sid" ch-smoke clickhouse \
      '{"host":"ch-11","port":8123,"user":"default","password":"password","dbname":"default","ssl":false}' \
      'SELECT 1 AS one' || fail "clickhouse query did not complete"
    pass "queried clickhouse through ch-11"
  fi

  # starburst is the bundled driver, and it does speak to open-source Trino.
  # A catalog is required, and postgres is one of the five already defined.
  if docker ps --format '{{.Names}}' | grep -q '^trino$'; then
    retry 12 5 mb_query "$sid" trino-smoke starburst \
      '{"host":"trino","port":8080,"catalog":"postgres","schema":"public","user":"admin","ssl":false}' \
      'SELECT 1 AS one' || fail "trino query did not complete"
    pass "queried trino through the starburst driver"
  fi
}

# MLflow: the health endpoint answers long before artifact logging works, and
# artifacts are the part that breaks. A client uploads to the artifact store
# directly unless the server proxies, and s3://mlflow resolves only inside the
# odctl network, so a run that logs params but no artifact is the failure this
# asserts against.
smoke_mlflow() {
  retry 60 5 http_ok "http://127.0.0.1:5004/health" || fail "no HTTP response from :5004"
  local out
  out=$(mlflow_snippet log-run 2>/dev/null) || fail "could not log a run with a proxied artifact"
  # Proxied artifacts get an mlflow-artifacts:/ URI. An s3:// URI means the
  # server handed the client a location only reachable inside the network.
  grep -q "^mlflow-artifacts:" <<<"$out" || fail "artifact URI is not mlflow-artifacts:/: $out"
  grep -q "notes.txt" <<<"$out" || fail "artifact not listed back: $out"
  pass "logged a run with a proxied artifact and read it back"
  assert_metrics http://mlflow:5000/metrics
  smoke_model_server
  smoke_model_features
}

# The guide runs its Python on the host, with the client versions the server
# image pins, so read them from the Dockerfile the image is built from.
# mlflow_snippet <section> [sed expression] [timeout in seconds]: the optional
# sed expression changes the section before it runs, and the timeout stops a
# call that hangs, as a download from the host does without its setting.
mlflow_snippet() {
  local dockerfile="$SNIPPETS/../../src/odctl/resources/docker/mlflow/Dockerfile" mlflow xgboost
  local edit="${2:-}" limit="${3:-}"
  mlflow=$(grep -oE 'mlflow/mlflow:v[0-9.]+' "$dockerfile" | head -1 | cut -dv -f2)
  xgboost=$(grep -oE "xgboost~=[0-9.]+" "$dockerfile" | head -1 | cut -d= -f2)
  (cd "$(mktemp -d)" && cp "$SNIPPETS/mlflow/driver_score.py" . && snippet mlflow/steps.py "$1" \
    | if [ -n "$edit" ]; then sed -e "$edit"; else cat; fi \
    | GIT_PYTHON_REFRESH=quiet ${limit:+timeout -k 5 "$limit"} uv run --no-project --quiet --python 3.12 \
      --with "mlflow==$mlflow" --with "xgboost~=$xgboost" python -)
}

# mlflow-serve starts with the mlflow profile and waits idle while MODEL_URI is
# empty. A model has to exist before it can serve one, so this registers the
# guide's model, sets MODEL_URI as the guide does and runs its serve step.
smoke_model_server() {
  [ "$(docker inspect -f '{{.State.Health.Status}}' mlflow-serve 2>/dev/null)" = healthy ] \
    || fail "mlflow-serve is not waiting healthy with MODEL_URI empty"
  pass "mlflow-serve waiting idle with MODEL_URI empty"
  mlflow_snippet register-model >/dev/null 2>&1 || fail "could not register a model to serve"

  [ -f .odctl/.env ] || fail "no .odctl/.env to set MODEL_URI in"
  # A fresh line rather than an edit in place, so this works whether or not the
  # generated template still carries a MODEL_URI key.
  sed -i'' -e '/^MODEL_URI=/d' .odctl/.env
  cat "$SNIPPETS/mlflow/model-uri.env" >> .odctl/.env

  # Assert on the response body. The endpoint answers 200 with an error payload
  # when scoring fails, so a status code alone proves nothing was served. The
  # model can still be loading when `odctl up` returns, so wait and run again.
  local got
  got=$(run_snippet mlflow/commands.sh serve 2>/dev/null)
  if [[ "$got" != *'"predictions"'* ]]; then
    retry 30 5 http_ok "http://127.0.0.1:5003/ping" || fail "no HTTP response from :5003"
    got=$(run_snippet mlflow/commands.sh serve 2>/dev/null)
  fi
  case "$got" in
    *'"predictions"'*) pass "served models:/demo-model@champion and scored: $(tail -1 <<<"$got")" ;;
    *) fail "/invocations returned no predictions: ${got:-<empty>}" ;;
  esac

  # The server resolves the alias once, at start. Register a second version
  # whose trees split, so that it predicts differently. That moves champion to
  # it, and the server must keep answering as version 1 until the restart.
  local before="$(tail -1 <<<"$got")" stale rc out
  mlflow_snippet register-model 's/max_depth=2)/max_depth=2, min_child_weight=0)/' >/dev/null 2>&1 \
    || fail "could not register a second version of demo-model"
  stale=$(curl -s -X POST http://127.0.0.1:5003/invocations \
    -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}')
  [ "$stale" = "$before" ] || fail "the served model changed before a restart: '$stale', was '$before'"
  out=$(timeout 300 bash -o pipefail -c "$(snippet mlflow/commands.sh new-version)" 2>/dev/null); rc=$?
  [ "$rc" -ne 124 ] || fail "the restarted mlflow-serve gave no answer within 300 seconds"
  grep -q 'Restart complete' <<<"$out" || fail "odctl restart mlflow did not complete: $out"
  [ "$rc" -eq 0 ] || fail "the scoring request after the restart failed with exit $rc"
  got=$(tail -1 <<<"$out")
  case "$got" in
    *'Restart complete'*) fail "the restarted mlflow-serve answered with an empty body" ;;
    *'"predictions"'*) [ "$got" != "$before" ] || fail "the restarted server still serves version 1: $got" ;;
    *) fail "no predictions after the restart: $got" ;;
  esac
  pass "a new version behind the alias is served after odctl restart mlflow: $got"

  # From the host, a download works only with the setting the guide names. Without
  # it the call waits on presigned URLs for seaweed:8333 and never returns.
  local files
  files=$(mlflow_snippet download "" 120 2>&1) || fail "the download with the setting failed: $files"
  grep -q MLmodel <<<"$files" || fail "the downloaded model has no MLmodel file: $files"
  if mlflow_snippet download '/MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD/d' 45 >/dev/null 2>&1; then
    fail "the download worked without MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false, so the guide's reason is stale"
  fi
  pass "a registered model downloads from the host with the setting and not without it"
}

# A model that reads online features calls feast-serve over HTTP from inside
# mlflow-serve. This starts feast itself, applies the Flink guide's push source
# and pushes one value, then serves the guide's model against it.
smoke_model_features() {
  odctl up feast >/dev/null 2>&1 || fail "could not start feast for the features model"
  retry 40 5 http_ok "http://127.0.0.1:6566/health" || fail "Feast never answered on :6566"
  (cd "$SNIPPETS/feast-iceberg" && run_snippet feast-iceberg/commands.sh push-apply) >/dev/null 2>&1 \
    || fail "could not apply the Feast push source"
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%S)
  retry 12 5 curl -fsS -X POST http://127.0.0.1:6566/push -H 'Content-Type: application/json' \
    -d "{\"push_source_name\": \"driver_push\", \"allow_registry_cache\": false, \"df\": {\"driver_id\": [1001], \"conv_rate\": [0.9], \"event_timestamp\": [\"$now\"]}}" \
    >/dev/null 2>&1 || fail "could not push a feature value to Feast"
  mlflow_snippet features-model >/dev/null 2>&1 || fail "could not register the features model"
  sed -i'' -e '/^MODEL_URI=/d' .odctl/.env
  cat "$SNIPPETS/mlflow/model-uri-features.env" >> .odctl/.env
  odctl recreate mlflow >/dev/null 2>&1 || fail "could not recreate mlflow-serve with the features model"
  retry 30 5 http_ok "http://127.0.0.1:5003/ping" || fail "no HTTP response from :5003 for the features model"
  local got
  # feast-serve caches its registry for up to a minute after apply, and until it
  # refreshes the model gets an error from it, so score again until it answers.
  for _ in $(seq 1 24); do
    got=$(run_snippet mlflow/commands.sh features-score 2>/dev/null)
    grep -Eq '"predictions": ?\[' <<<"$got" && break
    sleep 5
  done
  grep -Eq '"predictions": ?\[1\]' <<<"$got" || fail "the features model did not score driver 1001 as 1: ${got:-<empty>}"
  odctl down feast >/dev/null 2>&1 || fail "could not stop feast after the features model"
  pass "mlflow-serve scored a driver with a feature read from feast-serve: $got"
}

# Airflow: a healthy api-server proves nothing. On Airflow 3 the profile shipped
# for months with no dag-processor, so DAG files were never parsed, and then with
# tasks that could not reach the Execution API and whose tokens were rejected.
# The container was healthy through all of it. Only a DAG run reaching success
# catches that, so this drives one the whole way: into s3://airflow, through the
# S3 DAG bundle, past the parser, to a task that actually executes.
smoke_airflow() {
  retry 60 5 http_ok "http://127.0.0.1:8085/api/v2/monitor/health" \
    || fail "no HTTP response from :8085"

  # Every component, because the endpoint answers even when one is missing.
  local health
  health=$(curl -fsS --max-time 10 "http://127.0.0.1:8085/api/v2/monitor/health" 2>/dev/null)
  printf '%s' "$health" | python3 -c '
import json, sys
d = json.load(sys.stdin)
bad = [p for p in ("metadatabase", "scheduler", "dag_processor", "triggerer")
       if d.get(p, {}).get("status") != "healthy"]
if bad:
    sys.exit("unhealthy: " + ", ".join(bad))
' || fail "airflow component unhealthy: $health"
  pass "metadatabase, scheduler, dag_processor and triggerer all healthy"

  # standalone forces SimpleAuthManager, so check the fixed login still holds.
  curl -fsS --max-time 10 -X POST "http://127.0.0.1:8085/auth/token" \
    -H 'Content-Type: application/json' -d '{"username":"user","password":"password"}' \
    | grep -q access_token || fail "login as user/password was refused"
  pass "login as user/password works"

  # Written to s3://airflow only. The S3 DAG bundle reads it from there, so this
  # tests the real path rather than a file placed in the container.
  run_snippet airflow-dags/commands.sh upload >/dev/null 2>&1 \
    || fail "could not upload the DAG to s3://airflow/dags"

  # The bundle refreshes every 30 seconds, then the dag-processor parses it.
  retry 30 10 bash -c \
    "docker exec airflow airflow dags list 2>/dev/null | grep -q hello" \
    || fail "the S3 DAG bundle never delivered the DAG, or it was never parsed"
  pass "the S3 DAG bundle delivered the DAG and it was parsed"

  run_snippet airflow-dags/commands.sh run >/dev/null 2>&1 \
    || fail "the guide's list, unpause, trigger and list-runs commands failed"

  local state=""
  for _ in $(seq 1 30); do
    state=$(docker exec airflow airflow dags list-runs hello -o plain 2>/dev/null \
      | grep -E "^hello" | head -1 | tr -s ' ' | cut -d' ' -f3)
    case "$state" in success|failed) break ;; esac
    sleep 10
  done
  [ "$state" = "success" ] || fail "DAG run finished in state ${state:-none}, not success"
  pass "DAG run reached success, so a task really executed"

  # Airflow pushes OTLP to the telemetry collector rather than being scraped.
  assert_pushed_metrics 'airflow_.+' Airflow
}

# deps is a one-shot copy into a shared volume, so there is no container to
# probe afterwards. Every Flink and Spark profile mounts that volume read-only
# and copies jars out of it, and `cp ... || true` there means a missing jar is
# silent until a connector factory cannot be found at query time. Assert the
# directories the consumers actually read.
smoke_deps() {
  local vol=odctl-shared-deps
  docker volume inspect "$vol" >/dev/null 2>&1 || fail "$vol does not exist"

  # Read through a throwaway container, because init-deps has already exited.
  local listing
  listing=$(docker run --rm -v "$vol":/d alpine sh -c 'ls /d' 2>/dev/null)
  [ -n "$listing" ] || fail "$vol is empty, so init-deps copied nothing"

  local missing=""
  for dir in shared flink spark; do
    printf '%s\n' "$listing" | grep -qx "$dir" || missing="$missing $dir"
  done
  [ -z "$missing" ] && pass "shared-deps holds:$(printf ' %s' $listing)" \
    || fail "shared-deps is missing:$missing (has:$(printf ' %s' $listing))"

  # A directory can exist and hold nothing, which is the same failure later.
  local jars
  jars=$(docker run --rm -v "$vol":/d alpine sh -c 'find /d -name "*.jar" | wc -l' 2>/dev/null | tr -d '[:space:]')
  [ "${jars:-0}" -gt 0 ] || fail "no jars under $vol, so the Flink and Spark copies would be silent no-ops"
  pass "$jars jars present for the Flink and Spark profiles to copy"

  # The HTTP jar for Flink and the Kafka and Avro jars for Spark are not checked by name above.
  local jar
  for jar in flink/2.x/http.jar spark/spark-sql-kafka.jar spark/spark-token-provider-kafka.jar \
      spark/kafka-clients.jar spark/commons-pool2.jar spark/spark-avro.jar; do
    docker run --rm -v "$vol":/d alpine sh -c "[ -s /d/$jar ]" || fail "$jar is missing or empty in $vol"
  done
  pass "the Flink HTTP jar, the four Spark Kafka jars and the Spark Avro jar are in $vol"

  # An upgrade must not leave the previous version's jars beside the new ones:
  # Kafka Connect loaded Debezium 3.5.1 over 3.7.0 that way (#126). Plant a jar
  # the image does not ship, run deps again, and expect it gone.
  docker run --rm -v "$vol":/d alpine sh -c \
    'mkdir -p /d/connect/old-plugin && echo x > /d/connect/old-plugin/stale-1.0.jar' \
    || fail "could not plant a stale jar in $vol"
  odctl up deps >/dev/null 2>&1 || fail "odctl up deps failed on the second run"
  docker run --rm -v "$vol":/d alpine sh -c '[ ! -e /d/connect/old-plugin ]' \
    || fail "a jar the image does not ship stayed in $vol after odctl up deps"
  pass "deps removed a jar the image no longer ships"
}

# Prometheus: /-/ready answers before the config is loaded, and a scrape config
# an image bump moved looks identical from outside. The matrix runs telemetry on
# its own, so the services it scrapes are absent and 8 of 9 targets are legitimately
# down. Assert what holds alone: the config parsed into targets, the self-scrape
# works, a query returns data, OTLP reaches Prometheus both directly and through
# the collector, and Grafana logs in, queries Prometheus and loads odctl's
# dashboards. All of it runs in the one grafana/otel-lgtm container.
smoke_telemetry() {
  retry 60 5 http_ok "http://127.0.0.1:19090/-/ready" || fail "no HTTP response from :19090"

  # The self-scrape target reports unknown until the first scrape completes,
  # one scrape_interval after start, so this has to be retried.
  retry 24 5 bash -c '
    curl -fsS --max-time 10 "http://127.0.0.1:19090/api/v1/targets?state=active" 2>/dev/null \
      | python3 -c "
import json, sys
t = json.load(sys.stdin)[\"data\"][\"activeTargets\"]
jobs = {x[\"labels\"].get(\"job\") for x in t}
up = [x for x in t if x[\"labels\"].get(\"job\") == \"prometheus\" and x[\"health\"] == \"up\"]
sys.exit(0 if (t and \"prometheus\" in jobs and up) else 1)
"' || fail "prometheus never reported a loaded scrape config with its self-scrape up"
  pass "scrape config loaded and the self-scrape target is up"

  curl -fsS --max-time 10 "http://127.0.0.1:19090/api/v1/query?query=up" 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
if d.get("status") != "success" or not d["data"]["result"]:
    sys.exit("PromQL returned no series for up")
' || fail "prometheus could not answer a PromQL query"
  pass "PromQL query returned series"

  # The OTLP receiver is off by default, so this asserts the flag took effect
  # and that a metric posted over OTLP is queryable afterwards. Prometheus
  # accepts the JSON encoding, which keeps this to curl with no SDK.
  ts=$(python3 -c "import time;print(int(time.time()*1e9))")
  cat > /tmp/odctl-otlp.json <<JSON
{"resourceMetrics":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"odctl-smoke"}}]},
"scopeMetrics":[{"scope":{"name":"smoke"},"metrics":[{"name":"odctl_smoke_total","unit":"1",
"sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[
{"asDouble":42,"timeUnixNano":"${ts}","startTimeUnixNano":"${ts}","attributes":[]}]}}]}]}]}
JSON
  curl -fsS --max-time 10 -X POST -H "Content-Type: application/json" \
    --data-binary @/tmp/odctl-otlp.json \
    "http://127.0.0.1:19090/api/v1/otlp/v1/metrics" >/dev/null \
    || fail "prometheus rejected an OTLP metric, check --web.enable-otlp-receiver"
  retry 12 5 bash -c '
    curl -fsS --max-time 10 "http://127.0.0.1:19090/api/v1/query?query=odctl_smoke_total" 2>/dev/null \
      | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d[\"data\"][\"result\"]
sys.exit(0 if r and r[0][\"value\"][1] == \"42\" else 1)
"' || fail "the OTLP metric never became queryable"
  pass "OTLP metrics receiver accepted a metric and it queried back"

  # The guide's metric, through the collector's OTLP HTTP receiver, which
  # forwards to Prometheus. This is the path an OpenTelemetry SDK uses.
  run_snippet telemetry/commands.sh send-metric >/dev/null 2>&1 \
    || fail "the OTLP collector rejected a metric on :4318"
  retry 12 5 bash -c '
    curl -fsS --max-time 10 "http://127.0.0.1:19090/api/v1/query?query=demo_total" 2>/dev/null \
      | python3 -c "
import json, sys
r = json.load(sys.stdin)[\"data\"][\"result\"]
sys.exit(0 if r and r[0][\"value\"][1] == \"42\" else 1)
"' || fail "a metric sent to the collector never reached Prometheus"
  pass "OTLP collector on :4318 forwarded a metric to Prometheus"

  # Grafana: the image enables anonymous Admin by default, and odctl turns that off
  # in favour of user/password, so both the login and the data source are checked.
  retry 30 5 http_ok "http://127.0.0.1:3004/api/health" || fail "grafana never answered on :3004"
  curl -sS --max-time 10 -o /dev/null -w "%{http_code}" "http://127.0.0.1:3004/api/datasources" 2>/dev/null \
    | grep -q "^401$" || fail "grafana answered without a login, anonymous access is still on"
  curl -fsS --max-time 10 -u user:password \
    "http://127.0.0.1:3004/api/datasources/proxy/uid/prometheus/api/v1/query?query=up" 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d.get("status") == "success" and d["data"]["result"] else "no series")
' || fail "grafana could not query prometheus through its data source"
  pass "grafana logs in as user/password and queries prometheus"

  # A dashboard that fails to parse is logged and skipped, so count what loaded.
  local want
  want=$(find .odctl/grafana/dashboards -name '*.json' | wc -l | tr -d '[:space:]')
  [ "$want" -gt 0 ] || fail "no dashboards in .odctl/grafana/dashboards"
  retry 12 5 bash -c "
    curl -fsS --max-time 10 -u user:password 'http://127.0.0.1:3004/api/search?type=dash-db' 2>/dev/null \
      | python3 -c 'import json, sys
sys.exit(0 if sum(d.get(\"folderTitle\") == \"odctl\" for d in json.load(sys.stdin)) == $want else 1)'
  " || fail "grafana did not load all $want dashboards into the odctl folder"
  pass "grafana loaded all $want dashboards into the odctl folder"
}

# Marquez: the namespaces endpoint answers on an empty database, so it proves
# only that the service started. Lineage is the product, so post a real
# OpenLineage event and read the dataset back out.
smoke_lineage() {
  retry 60 5 http_ok "http://127.0.0.1:5002/api/v1/namespaces" || fail "no HTTP response from :5002"
  run_snippet lineage/commands.sh send >/dev/null 2>&1 || fail "could not post the OpenLineage events"
  pass "posted START and COMPLETE OpenLineage events"

  # Marquez writes the job, run and dataset from those events. Reading them
  # back proves it persisted them rather than accepting and dropping.
  retry 12 5 lineage_read_back || fail "the job or the dataset never read back from Marquez"
  pass "dataset and job both read back from Marquez"
  assert_metrics http://marquez-api:5000/metrics
}

lineage_read_back() {
  local out
  out=$(run_snippet lineage/commands.sh read 2>/dev/null)
  grep -q '"name":"demo-job"' <<<"$out" && grep -q '"name":"demo-dataset"' <<<"$out"
}

# Fluss: both containers ran while the cluster did nothing at all. The
# coordinator pointed at a ZooKeeper hostname that did not exist, then at a
# ClickHouse Keeper that rejects opcode 19 and dropped the session every eight
# seconds. Neither port was ever open. Assert the cluster formed, not that the
# processes are alive.
smoke_fluss() {
  for c in fluss-zookeeper fluss-coordinator fluss-tablet-1; do
    local state
    state=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null) || fail "$c does not exist"
    [ "$state" = "running" ] || fail "$c is $state, not running"
  done
  pass "zookeeper, coordinator and tablet server all running"

  # bind.listeners binds the container hostname, so localhost is refused here.
  for c in fluss-coordinator fluss-tablet-1; do
    retry 24 5 docker exec "$c" bash -c "timeout 3 bash -c '</dev/tcp/$c/9123'" \
      || fail "$c is not accepting connections on 9123"
  done
  pass "coordinator and tablet server both accept client connections"

  # The registrations live in ZooKeeper, so this proves the cluster formed
  # rather than that two processes opened a socket. Retried, because a port
  # opens before the server has written its node.
  retry 24 5 bash -c \
    "docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids 2>/dev/null | grep -q '\[0'" \
    || fail "no tablet server registered in ZooKeeper"
  pass "tablet server 0 registered in ZooKeeper"

  retry 24 5 bash -c \
    "docker exec fluss-zookeeper zkCli.sh -server localhost:2181 get /fluss/coordinators/active 2>/dev/null | grep -q fluss-coordinator:9123" \
    || fail "no active coordinator registered in ZooKeeper"
  pass "coordinator registered itself as the active leader"
  local out
  out=$(run_snippet fluss/commands.sh registrations 2>/dev/null)
  grep -q '\[0' <<<"$out" && grep -q fluss-coordinator:9123 <<<"$out" \
    || { echo "$out"; fail "the guide's ZooKeeper commands did not show the registrations"; }
  assert_metrics http://fluss-coordinator:9249/metrics http://fluss-tablet-1:9249/metrics

  # The Flink client jar comes from the deps image and must match the server
  # version, so write and read a table through it, with the guide's SQL.
  odctl up flink-lite >/dev/null 2>&1 || fail "could not start flink-lite for the Fluss client check"
  retry 40 5 http_ok "http://127.0.0.1:8082/config" || fail "JobManager REST never answered"
  out=$(snippet fluss/steps.sql table | docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh 2>&1)
  local got
  got=$(grep -cE '^\| +[123] \| +[abc] +\|$' <<<"$out")
  [ "$got" -eq 3 ] || { echo "$out" | tail -30; fail "Flink read $got of 3 rows from a Fluss table"; }
  pass "Flink wrote 3 rows to a Fluss table and read them back"
}

# OpenMetadata: the version endpoint answers through every failure the 2.0.1
# upgrade could cause. The ingestion container runs its own Airflow 3, whose
# health path moved to /api/v2/monitor/health, and a stale image or a failed
# migration both leave a server that still reports a version. Drive the whole
# path: migrate, login, a real ingestion, then the 2.0 features the upgrade was
# for.
smoke_metadata() {
  retry 90 5 http_ok "http://127.0.0.1:8585/api/v1/system/version" \
    || fail "no HTTP response from :8585"

  local migrate
  migrate=$(docker inspect -f '{{.State.ExitCode}}' openmetadata-migrate 2>/dev/null || echo NA)
  [ "$migrate" = "0" ] || fail "openmetadata-migrate exited $migrate, so the schema is not migrated"
  pass "schema migration completed"
  assert_metrics http://openmetadata-server:8586/prometheus

  # The principal domain odctl sets is open-data.local, not the upstream
  # default. A wrong domain fails with a misleading invalid password error.
  local token
  token=$(om_step login 'echo "$TOKEN"' 2>/dev/null | tail -1)
  [ -n "$token" ] || fail "admin@open-data.local could not log in"
  pass "admin logged in and received a JWT"
  local auth="Authorization: Bearer $token"

  # Airflow 3 moved this path. The old /health returns 404 with a message saying so.
  retry 60 5 http_ok "http://127.0.0.1:8087/api/v2/monitor/health" \
    || fail "ingestion Airflow never answered on 8087"
  docker exec openmetadata-server sh -c \
    'wget -q -O- http://openmetadata-ingestion:8080/api/v2/monitor/health' >/dev/null 2>&1 \
    || fail "the server cannot reach the ingestion container, so no pipeline can deploy"
  pass "ingestion Airflow healthy and reachable from the server"

  # A real ingestion, with the guide's steps. Postgres is already running, so it
  # is its own source.
  local svc
  svc=$(TOKEN="$token" om_step service 'echo "$SVC"' 2>/dev/null | tail -1)
  [ -n "$svc" ] || fail "could not create a database service"

  local out pipe
  out=$(TOKEN="$token" SVC="$svc" om_step pipeline 'echo; echo "$PIPE"' 2>/dev/null)
  pipe=$(tail -1 <<<"$out")
  [ -n "$pipe" ] || fail "could not create an ingestion pipeline"
  grep -q 'has been created' <<<"$out" || { echo "$out"; fail "the pipeline did not deploy a DAG into Airflow"; }
  pass "ingestion pipeline deployed a DAG"

  # Airflow's dag_processor has to parse the new file before it can be
  # triggered, so the guide's trigger can come too early. Trigger again here.
  if ! grep -q 'has been triggered' <<<"$out"; then
    local triggered=no
    for _ in $(seq 1 24); do
      if curl -fsS --max-time 90 -X POST -H "$auth" \
          "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/trigger/$pipe" 2>/dev/null \
          | grep -q 'has been triggered'; then triggered=yes; break; fi
      sleep 5
    done
    [ "$triggered" = "yes" ] || fail "the pipeline never triggered"
  fi

  local state=""
  for _ in $(seq 1 30); do
    state=$(TOKEN="$token" om_step status 2>/dev/null \
      | python3 -c 'import json,sys; s=json.load(sys.stdin).get("pipelineStatuses") or []; print(s[0]["pipelineState"] if s else "")' 2>/dev/null)
    case "$state" in success|failed|partialSuccess) break ;; esac
    sleep 10
  done
  [ "$state" = "success" ] || fail "ingestion run finished in state ${state:-none}, not success"
  pass "ingestion run reached success"

  # Elasticsearch moved to 9.3.0 with this upgrade, so assert the catalogue is
  # searchable rather than merely populated. The guide's step starts indexing
  # and searches once; the index fills over the next minutes.
  TOKEN="$token" om_step search >/dev/null 2>&1 || fail "the guide's search step failed"
  local hits=0
  for _ in $(seq 1 60); do
    hits=$(curl -fsS --max-time 20 -H "$auth" \
      'http://127.0.0.1:8585/api/v1/search/query?q=*&index=table_search_index&size=1' 2>/dev/null \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["hits"]["total"]["value"])' 2>/dev/null || echo 0)
    [ "${hits:-0}" -gt 100 ] && break
    sleep 5
  done
  [ "${hits:-0}" -gt 100 ] || fail "only ${hits:-0} tables searchable in Elasticsearch"
  pass "$hits tables ingested and searchable through Elasticsearch"

  # 2.0 features the upgrade was for. A 1.13 server has neither.
  curl -fsS --max-time 15 -X POST "http://127.0.0.1:8585/mcp" -H "$auth" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"odctl-smoke","version":"1"}}}' \
    2>/dev/null | grep -q serverInfo || fail "the MCP server did not answer an initialize handshake"
  pass "MCP server completed an initialize handshake"

  for collection in contextCenter/pages contextCenter/memories; do
    curl -fsS --max-time 10 -H "$auth" \
      "http://127.0.0.1:8585/api/v1/$collection?limit=1" >/dev/null 2>&1 \
      || fail "2.0 API /v1/$collection does not answer"
  done
  pass "Context Center pages and memories both answer"

  TOKEN="$token" om_step remove >/dev/null 2>&1 || fail "the guide's remove step failed"
  pass "the guide's remove step deleted the service and its pipeline"
}

# The OpenMetadata guide's steps share shell variables: login sets TOKEN, the
# service step sets SVC from AUTH, and so on. Run one section with the
# variables earlier steps set, passed in the environment, then any extra
# commands, such as echoing the variable the section set.
om_step() {
  local code
  code=$(snippet openmetadata/commands.sh "$1")
  bash -o pipefail -c 'AUTH="Authorization: Bearer ${TOKEN:-}"
'"$code"'
'"${2:-}"
}

# Feast keeps no feature values of its own, so liveness proves nothing here.
# This builds a real Iceberg table through the catalog, registers a feature view
# over it, takes a point-in-time join, materializes to Valkey and reads it back.
# A failure in any of those is a broken profile even when both containers are up.
smoke_feast() {
  retry 60 5 http_ok "http://127.0.0.1:8890/api/v1/projects" || fail "no HTTP response from the feast UI on :8890"
  pass "feast UI answering, registry reachable"
  retry 30 5 http_ok "http://127.0.0.1:6566/health" || fail "no HTTP response from the feast online server on :6566"
  pass "feast online server answering"
  assert_metrics http://feast-serve:8000/metrics

  local work="${TMPDIR:-/tmp}/odctl-feast-smoke"
  rm -rf "$work"; mkdir -p "$work/feature_repo"

  # The offline half runs in the caller's environment, not in the container:
  # the published image carries feast[minimal], which has no iceberg or duckdb.
  uv venv "$work/.venv" >/dev/null 2>&1 || fail "could not create a venv for the feast client"
  VIRTUAL_ENV="$work/.venv" uv pip install -q \
    "feast[duckdb,iceberg,redis,postgres]==0.66.0" "pyarrow" >/dev/null 2>&1 \
    || fail "could not install the feast client"

  # Repository from the guide, with warehouse="" in its source. Feast's REST client
  # puts warehouse into the URL path as a prefix for Polaris and Nessie style
  # catalogs, and Iceberg's REST fixture server serves the spec with no prefix,
  # so a real warehouse gives HTTP 400 "Ambiguous URI empty segment".
  cp "$SNIPPETS/feast-iceberg/feature_repo/"* "$work/feature_repo/"
  # Its own project, because the guide's Runnable Example registers the same
  # feature view in demo afterwards. feast teardown leaves the view's row in
  # feature_view_version_history, so a second apply in demo fails on its key.
  sed 's/^project: demo$/project: smoke/' "$work/feature_repo/feature_store.yaml" \
    > "$work/feature_store.yaml" && mv "$work/feature_store.yaml" "$work/feature_repo/feature_store.yaml"

  cat > "$work/check.py" <<'PYCHECK'
import datetime, sys, pandas as pd
from feast import FeatureStore
fs = FeatureStore(repo_path="feature_repo")
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
hist = fs.get_historical_features(
    entity_df=pd.DataFrame({"driver_id": [1001, 1002], "event_timestamp": [now] * 2}),
    features=["driver_stats:conv_rate"],
).to_df().sort_values("driver_id")
if list(hist["conv_rate"].round(2)) != [0.5, 0.75]:
    sys.exit(f"point-in-time join returned {list(hist['conv_rate'])}")
print("offline ok")
PYCHECK

  cat > "$work/online.py" <<'PYONLINE'
import sys
from feast import FeatureStore
fs = FeatureStore(repo_path="feature_repo")
r = fs.get_online_features(
    features=["driver_stats:conv_rate"],
    entity_rows=[{"driver_id": 1001}, {"driver_id": 1002}],
).to_dict()
got = [round(v, 2) for v in r["conv_rate"]]
if got != [0.5, 0.75]:
    sys.exit(f"online read returned {got}")
print("online ok")
PYONLINE

  # Catalog settings from the guide, exported as the guide does.
  eval "$(snippet feast-iceberg/commands.sh catalog-env)"
  snippet feast-iceberg/steps.py create-table > "$work/build.py"

  local py="$work/.venv/bin/python"
  local feast_bin="$work/.venv/bin/feast"
  local log="$work/step.log"

  # Output goes to a file rather than /dev/null: a swallowed stderr here turns
  # a one-line cause into an afternoon, so a failure prints what actually broke.
  run_step() {
    local what="$1"; shift
    if ! (cd "$work" && "$@") >"$log" 2>&1; then
      echo "---- $what ----"
      tail -25 "$log"
      fail "$what"
    fi
  }

  run_step "could not create the Iceberg table through the catalog" "$py" build.py
  pass "Iceberg table created through the REST catalog on SeaweedFS"

  run_step "feast apply or materialize failed" \
    env PATH="$work/.venv/bin:$PATH" bash -o pipefail -c "$(snippet feast-iceberg/commands.sh apply-materialize)"
  pass "feast apply registered the feature view, and materialize wrote to valkey"

  run_step "the point-in-time join returned the wrong values" "$py" check.py
  pass "get_historical_features read Iceberg through DuckDB"

  run_step "the online read from valkey returned the wrong values" "$py" online.py
  pass "get_online_features read the materialised values from valkey"

  (cd "$work" && "$feast_bin" -c feature_repo teardown) >/dev/null 2>&1 || true
  curl -fsS --max-time 10 -X DELETE \
    "http://127.0.0.1:8181/v1/namespaces/demo/tables/driver_stats?purgeRequested=true" >/dev/null 2>&1 || true
  curl -fsS --max-time 10 -X DELETE "http://127.0.0.1:8181/v1/namespaces/demo" >/dev/null 2>&1 || true
  # The venv stays: the guide's Runnable Example runs with it next, and the feast
  # case removes $work after that.
}

# Temporal: a healthy server proves only that it answers. Workflows run in the
# caller's worker, so this runs one with the temporalio SDK from the host: an
# activity that fails once and succeeds on retry, and a workflow that waits for
# a signal. A third workflow is left waiting across `odctl restart`, then
# signalled, which proves the history in the database file survived and the
# workflow resumed from it.
smoke_temporal() {
  retry 60 5 http_ok "http://127.0.0.1:8233" || fail "no HTTP response from the Web UI on :8233"
  pass "Web UI answering on :8233"

  local work="${TMPDIR:-/tmp}/odctl-temporal-smoke"
  rm -rf "$work"; mkdir -p "$work"
  uv venv "$work/.venv" >/dev/null 2>&1 || fail "could not create a venv for the temporal client"
  VIRTUAL_ENV="$work/.venv" uv pip install -q "temporalio==1.34.0" >/dev/null 2>&1 \
    || fail "could not install the temporalio SDK"

  # The worker step as the guide writes it, then the Runnable Example, which
  # adds the Approval workflow and its signal to the same script.
  snippet temporal-workers/steps.py worker > "$work/greet.py"
  local got
  got=$(cd "$work" && "$work/.venv/bin/python" greet.py 2>&1 | tail -1)
  [ "$got" = "hello odctl" ] || fail "the guide's worker printed '$got', expected hello odctl"
  got=$(cd "$work" && "$work/.venv/bin/python" "$SNIPPETS/temporal-workers/example.py" 2>&1 | tail -1)
  [ "$got" = "approved by alice" ] || fail "the guide's example printed '$got', expected approved by alice"
  pass "the guide's worker retried its activity, and its approval workflow completed on a signal"

  cat > "$work/workflows.py" <<'PYEOF'
import asyncio, os, sys
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import RetryPolicy
from temporalio.worker import Worker


@activity.defn
async def greet(name: str) -> str:
    # Fails on the first attempt, so a result means the retry policy ran it again.
    if activity.info().attempt < 2:
        raise RuntimeError("first attempt fails on purpose")
    return f"hello {name}"


@workflow.defn
class Greet:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            greet, name,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=3),
        )


@workflow.defn
class Approval:
    def __init__(self) -> None:
        self.approver = None

    @workflow.signal
    def approve(self, approver: str) -> None:
        self.approver = approver

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approver is not None)
        return f"approved by {self.approver}"


async def status(client, workflow_id):
    return (await client.get_workflow_handle(workflow_id).describe()).status


async def approve(client, workflow_id, approver):
    if await status(client, workflow_id) != WorkflowExecutionStatus.RUNNING:
        sys.exit(f"{workflow_id} is not waiting for its signal")
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(Approval.approve, approver)
    got = await asyncio.wait_for(handle.result(), 60)
    if got != f"approved by {approver}":
        sys.exit(f"{workflow_id} returned {got!r}")


async def main(phase: str) -> None:
    run = os.environ["SMOKE_RUN"]
    client = await Client.connect(os.environ["SMOKE_ADDRESS"])
    queue = f"odctl-smoke-{run}"
    async with Worker(client, task_queue=queue, workflows=[Greet, Approval], activities=[greet]):
        if phase == "run":
            got = await client.execute_workflow(
                Greet.run, "odctl", id=f"greet-{run}", task_queue=queue,
                execution_timeout=timedelta(seconds=60),
            )
            if got != "hello odctl":
                sys.exit(f"greet-{run} returned {got!r}")
            for workflow_id in (f"approval-{run}", f"pending-{run}"):
                await client.start_workflow(Approval.run, id=workflow_id, task_queue=queue)
            await approve(client, f"approval-{run}", "smoke")
            if await status(client, f"pending-{run}") != WorkflowExecutionStatus.RUNNING:
                sys.exit(f"pending-{run} is not waiting for its signal")
        else:
            if await status(client, f"greet-{run}") != WorkflowExecutionStatus.COMPLETED:
                sys.exit(f"greet-{run} is not in the history as completed")
            await approve(client, f"pending-{run}", "resume")
    print(f"{phase} ok")


# The workflow sandbox imports this file again, so running main on import fails.
if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
PYEOF

  export SMOKE_RUN="$$-$(date -u +%Y%m%d%H%M%S)" SMOKE_ADDRESS="127.0.0.1:7233"
  local py="$work/.venv/bin/python" log="$work/step.log"

  # Output goes to a file, so a failure prints what broke rather than nothing.
  run_temporal() {
    local what="$1"; shift
    if ! (cd "$work" && "$py" workflows.py "$@") >"$log" 2>&1; then
      echo "---- $what ----"
      tail -25 "$log"
      fail "$what"
    fi
  }

  run_temporal "the workflows did not complete against 127.0.0.1:7233" run
  pass "an activity succeeded on retry, and a workflow completed once its signal was sent"

  assert_metrics http://temporal:9090/metrics

  # A restart keeps the container, so the database file and its history stay.
  odctl restart temporal >/dev/null 2>&1 || fail "odctl restart temporal failed"
  retry 24 5 docker exec temporal temporal operator cluster health --address 127.0.0.1:7233 >/dev/null 2>&1 \
    || fail "temporal did not become healthy after odctl restart"
  run_temporal "history did not survive odctl restart" resume
  pass "history survived odctl restart, and a waiting workflow resumed and completed"

  rm -rf "$work"
}

# Evidently answers /api/version with no database behind it, and its dataset
# files go to a different store from its reports. So this pushes a data drift
# report and reads it back through the API, which proves Postgres, and stores a
# dataset and finds its file under s3://evidently, which proves SeaweedFS and
# the s3fs the odctl image adds. It runs in the container, which already has
# the evidently client.
smoke_evidently() {
  retry 60 5 http_ok "http://127.0.0.1:8089/api/v2/projects" || fail "no HTTP response from :8089"
  pass "evidently answering and its database reachable"

  # The guide's two steps run on the host in one process, as a reader runs them,
  # with the client version the compose file pins. The checks after them read
  # back what the steps stored.
  local version
  version=$(grep -oE 'evidently/evidently-service:[0-9.]+' \
    "$SNIPPETS/../../src/odctl/resources/compose-mlops.yml" | head -1 | cut -d: -f2)
  {
    snippet evidently-reports/steps.py report
    snippet evidently-reports/steps.py dataset
    cat <<'PYEOF'
import sys, requests
url = "http://127.0.0.1:8089"
# Column x moves by three standard deviations and y does not, so exactly one
# column should drift.
listed = requests.get(f"{url}/api/projects/{project.id}/snapshots", timeout=30).json()
if len(listed) != 1:
    sys.exit(f"expected one report listed back, got {listed}")
stored = requests.get(f"{url}/api/projects/{project.id}/{listed[0]['id']}/download",
                      params={"report_format": "json"}, timeout=30).json()
drift = next(m for m in stored["metrics"] if m["metric_name"].startswith("DriftedColumnsCount"))
if drift["value"]["count"] != 1:
    sys.exit(f"stored report has {drift['value']} drifted columns, expected 1")
back = ws.load_dataset(dataset_id).as_dataframe()
pd.testing.assert_frame_equal(back[list(data.columns)].reset_index(drop=True), data, check_dtype=False)
ws.delete_project(project.id)
PYEOF
  } | (cd "$(mktemp -d)" && uv run --no-project --quiet --python 3.12 \
      --with "evidently==$version" --with "pandas<3.1" --with requests python -) \
    || fail "report or dataset round trip failed"
  pass "pushed a drift report and read it back, and a dataset round-tripped"
}

# A profile with no functional assertion yet still has to expose its endpoint.
smoke_http_only() {
  local url="$1"
  retry 60 5 http_ok "$url" || fail "no HTTP response from $url"
  pass "HTTP endpoint answering at $url"
}

# The metrics targets for these profiles are the ones prometheus.yml lists for
# each, except Spark's applications endpoint. It has samples only once an
# application registers with the master, and smoke_spark's spark-sql runs in
# local mode, so none does.
KAFKA_SIDE=(http://connect:9404/metrics http://karapace:8081/metrics)
SPARK_MASTER=http://spark-master:8080/metrics/master/prometheus/

case "$PROFILE" in
  kafka-lite)
    guide_kafka; connect_plugins; connect_datagen; getting_started
    assert_metrics http://kafka:9404/metrics "${KAFKA_SIDE[@]}"
    smoke_iceberg_sink
    run_example kafka 'Processed a total of 5 messages'
    run_example kafka-connect 'Processed a total of 3 messages' ;;
  kafka-full)
    smoke_kafka kafka-1; connect_plugins
    assert_metrics http://kafka-{1,2,3}:9404/metrics "${KAFKA_SIDE[@]}" ;;
  flink-lite)
    smoke_flink
    smoke_flink_kafka_jdbc
    smoke_flink_http
    assert_metrics http://jobmanager:9249/metrics http://taskmanager-a:9249/metrics
    run_example flink-sql 'b +\| +1 +\| +7\.5'
    run_example rolling-windows '20 +\| +20'
    run_example iceberg-ingestion 'records written by the Kafka Connect sink' ;;
  flink-full)
    smoke_flink
    assert_metrics http://jobmanager:9249/metrics http://taskmanager-{a,b,c}:9249/metrics ;;
  spark-lite)
    smoke_spark
    assert_metrics "$SPARK_MASTER" http://spark-worker-1:8081/metrics/prometheus/
    run_example spark '"n":3' ;;
  spark-full)
    smoke_spark
    assert_metrics "$SPARK_MASTER" http://spark-worker-{1,2,3}:8081/metrics/prometheus/ ;;
  ch-lite)               smoke_ch_lite; run_example clickhouse 'ch-12 holds 50 rows' ;;
  ch-full)               smoke_ch_full ;;
  trino)                 smoke_trino; how_it_works_trino ;;
  deps)       smoke_deps ;;
  postgres|storage|catalog|valkey) smoke_infra ;;
  metabase)   smoke_metabase; run_example trino-metabase '"status":"ok"' ;;
  airflow)    smoke_airflow; run_example airflow-dags 'success'; how_it_works_airflow ;;
  temporal)   smoke_temporal ;;
  mlflow)
    smoke_mlflow
    how_it_works_edit mlops-deps .odctl/.env mlflow '^0\.9\.0$'
    how_it_works_edit timezone .odctl/.env mlflow '^AE[DS]T$'
    run_example mlflow '"predictions": \[0, 0\]' "$(mlflow_runner) bash" ;;
  lineage)    smoke_lineage; run_example lineage 'COMPLETED' ;;
  telemetry)  smoke_telemetry; run_example telemetry '"42"' ;;
  metadata)   smoke_metadata; run_example openmetadata 'removed demo_pg' ;;
  fluss)      smoke_fluss; run_example fluss '\| +3 +\| +c +\|' ;;
  feast)
    smoke_feast
    run_example feast-iceberg '0.8999999761581421' "env PATH=${TMPDIR:-/tmp}/odctl-feast-smoke/.venv/bin:$PATH bash"
    rm -rf "${TMPDIR:-/tmp}/odctl-feast-smoke" ;;
  evidently)  smoke_evidently; run_example evidently-reports 'report pushed to project' "$(evidently_runner)" ;;
  *)
    echo "ℹ️  $PROFILE: no functional assertion defined, checking containers only"
    [ "$(docker ps -q | wc -l)" -ge 1 ] || fail "no containers running"
    pass "containers running" ;;
esac
