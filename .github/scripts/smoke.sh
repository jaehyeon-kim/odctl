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
  local run_id="$$"
  retry 60 5 http_ok "http://127.0.0.1:5000/health" || fail "no HTTP response from :5000"
  docker exec -i -e SMOKE_RUN_ID="$run_id" -e GIT_PYTHON_REFRESH=quiet -e MLFLOW_LOGGING_LEVEL=ERROR mlflow python - <<'PYEOF' || fail "could not log a run with a proxied artifact"
import mlflow, os, pathlib, sys
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment(f"odctl-smoke-{os.environ['SMOKE_RUN_ID']}")
p = pathlib.Path("/tmp/smoke.txt")
p.write_text("odctl smoke")
with mlflow.start_run() as run:
    mlflow.log_param("k", "v")
    mlflow.log_metric("m", 1.0)
    mlflow.log_artifact(str(p))
    uri = mlflow.get_run(run.info.run_id).info.artifact_uri
# Proxied artifacts get an mlflow-artifacts:/ URI. An s3:// URI means the
# server handed the client a location only reachable inside the network.
if not uri.startswith("mlflow-artifacts:"):
    sys.exit(f"artifact_uri is {uri}, expected mlflow-artifacts:/")
names = [f.path for f in mlflow.MlflowClient().list_artifacts(run.info.run_id)]
if "smoke.txt" not in names:
    sys.exit(f"artifact not listed back: {names}")
PYEOF
  pass "logged a run with a proxied artifact and read it back"
  smoke_model_server "$run_id"
}

# The mlflow-serve profile is asserted here rather than as its own e2e matrix
# entry. The runner starts a profile before calling this script, and an empty
# MODEL_URI stops that container by design, so a standalone entry could only
# ever fail. A model has to exist first, which makes this the profile that can
# create one.
smoke_model_server() {
  local run_id="$1" name="odctl-smoke-$1"
  docker exec -i -e SMOKE_MODEL_NAME="$name" -e GIT_PYTHON_REFRESH=quiet -e MLFLOW_LOGGING_LEVEL=ERROR \
    mlflow python - <<'PYEOF' || fail "could not register a model to serve"
import mlflow, numpy as np, os, xgboost as xgb
from mlflow import MlflowClient
mlflow.set_tracking_uri("http://localhost:5000")
name = os.environ["SMOKE_MODEL_NAME"]
mlflow.set_experiment(name)
X, y = np.array([[0.0], [1.0], [2.0], [3.0]]), np.array([0, 0, 1, 1])
with mlflow.start_run():
    model = xgb.XGBClassifier(n_estimators=5, max_depth=2).fit(X, y)
    mlflow.xgboost.log_model(model, name="model", registered_model_name=name)
c = MlflowClient()
v = max(int(mv.version) for mv in c.search_model_versions(f"name='{name}'"))
c.set_registered_model_alias(name, "champion", v)
PYEOF

  [ -f .odctl/.env ] || fail "no .odctl/.env to set MODEL_URI in"
  # A fresh line rather than an edit in place, so this works whether or not the
  # generated template still carries a MODEL_URI key.
  sed -i'' -e '/^MODEL_URI=/d' .odctl/.env
  echo "MODEL_URI=\"models:/$name@champion\"" >> .odctl/.env

  odctl up mlflow-serve >/dev/null 2>&1 || fail "mlflow-serve did not start for models:/$name@champion"
  retry 30 5 http_ok "http://127.0.0.1:5003/ping" || fail "no HTTP response from :5003"

  # Assert on the response body. The endpoint answers 200 with an error payload
  # when scoring fails, so a status code alone proves nothing was served.
  local got
  got=$(curl -fsS --max-time 20 -X POST http://127.0.0.1:5003/invocations \
    -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}' 2>/dev/null)
  case "$got" in
    *'"predictions"'*) pass "served models:/$name@champion and scored: $got" ;;
    *) server_down; fail "/invocations returned no predictions: ${got:-<empty>}" ;;
  esac
  server_down
}

# Down by name, so tearing the mlflow profile down afterwards does not leave a
# container behind that depends on it. Not `yes | odctl down`: this script runs
# under pipefail, and odctl exits before `yes` does, so the pipeline reports
# SIGPIPE as 141 and the whole smoke test fails after passing.
server_down() {
  printf 'y\n' | odctl down mlflow-serve >/dev/null 2>&1 || true
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
  metabase)   smoke_metabase ;;
  airflow)    smoke_http_only "http://127.0.0.1:8085/api/v2/monitor/health" ;;
  mlflow)     smoke_mlflow ;;
  lineage)    smoke_http_only "http://127.0.0.1:5002/api/v1/namespaces" ;;
  telemetry)  smoke_http_only "http://127.0.0.1:19090/-/ready" ;;
  metadata)   smoke_http_only "http://127.0.0.1:8585/api/v1/system/version" ;;
  fluss)
    retry 40 5 bash -c 'docker ps --format "{{.Names}}" | grep -q fluss-coordinator' \
      || fail "coordinator container never appeared"
    # Neither fluss service sets a restart policy, so RestartCount can never
    # move and a crashed container simply exits. Assert the state directly, and
    # do it for the tablet server too, which nothing checked before. No consumer
    # drives Fluss yet, so staying up is the whole bar.
    for c in fluss-coordinator fluss-tablet-1; do
      state=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null) \
        || fail "$c does not exist"
      [ "$state" = "running" ] || fail "$c is $state, not running"
    done
    pass "coordinator and tablet server both running" ;;
  *)
    echo "ℹ️  $PROFILE: no functional assertion defined, checking containers only"
    [ "$(docker ps -q | wc -l)" -ge 1 ] || fail "no containers running"
    pass "containers running" ;;
esac
