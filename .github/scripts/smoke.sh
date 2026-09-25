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
      pass "accepting connections and running queries"
      # The image is pgvector/pgvector and 01-init-databases.sh creates the
      # extension in a `vector` database. SELECT 1 on `odctl` proves neither, so
      # retrieval work would fail at first use rather than here.
      docker exec postgres psql -U user -d vector -v ON_ERROR_STOP=1 -q -c "
        CREATE TABLE IF NOT EXISTS odctl_smoke (id bigserial primary key, embedding vector(3));
        TRUNCATE odctl_smoke;
        INSERT INTO odctl_smoke (embedding) VALUES ('[1,0,0]'), ('[0,1,0]'), ('[0.9,0.1,0]');
        CREATE INDEX IF NOT EXISTS odctl_smoke_hnsw ON odctl_smoke USING hnsw (embedding vector_l2_ops);
      " >/dev/null 2>&1 || fail "pgvector table, insert or HNSW index failed in the vector database"
      local nearest
      nearest=$(docker exec postgres psql -U user -d vector -tAc \
        "SELECT id FROM odctl_smoke ORDER BY embedding <-> '[1,0,0]' LIMIT 1" 2>/dev/null | tr -d '[:space:]')
      docker exec postgres psql -U user -d vector -q -c "DROP TABLE IF EXISTS odctl_smoke" >/dev/null 2>&1
      [ "$nearest" = "1" ] || fail "pgvector similarity returned row '$nearest', expected 1"
      pass "pgvector: vector column, HNSW index and similarity ordering all work" ;;
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
      pass "signed write, read back and delete through the S3 API" ;;
    catalog)
      retry 30 5 http_ok "http://127.0.0.1:8181/v1/config" || fail "REST catalog never answered"
      curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{"namespace":["smoke"]}' "http://127.0.0.1:8181/v1/namespaces" >/dev/null 2>&1
      curl -fsS "http://127.0.0.1:8181/v1/namespaces" 2>/dev/null | grep -q smoke \
        || fail "namespace create or list failed"
      pass "namespace created and listed through the REST API"
      # A namespace is metadata only. Creating a table exercises the JDBC
      # catalog backend and the S3FileIO write that every engine depends on.
      curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{"name":"t","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"id","required":true,"type":"long"}]}}' \
        "http://127.0.0.1:8181/v1/namespaces/smoke/tables" >/dev/null 2>&1 \
        || fail "table create failed against the REST catalog"
      curl -fsS "http://127.0.0.1:8181/v1/namespaces/smoke/tables/t" 2>/dev/null \
        | grep -q 'metadata-location' || fail "table metadata did not read back"
      curl -fsS -X DELETE "http://127.0.0.1:8181/v1/namespaces/smoke/tables/t" >/dev/null 2>&1 || true
      pass "table created through the catalog and its metadata read back" ;;
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
  retry 60 5 http_ok "http://127.0.0.1:5004/health" || fail "no HTTP response from :5004"
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

  local dag_id="odctl_smoke_$$"
  # Written to s3://airflow only. The S3 DAG bundle reads it from there, so this
  # tests the real path rather than a file placed in the container.
  docker exec -i airflow python - "$dag_id" >/dev/null 2>&1 <<'PYEOF' \
    || fail "could not upload the DAG to s3://airflow/dags"
import sys, boto3
dag_id = sys.argv[1]
body = f"""
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
import pendulum

with DAG(
    dag_id="{dag_id}",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
):
    BashOperator(task_id="say_hello", bash_command="echo odctl-smoke-ran")
"""
boto3.client("s3", endpoint_url="http://seaweed:8333").put_object(
    Bucket="airflow", Key=f"dags/{dag_id}.py", Body=body.encode())
PYEOF

  # The bundle refreshes every 30 seconds, then the dag-processor parses it.
  retry 30 10 bash -c \
    "docker exec airflow airflow dags list 2>/dev/null | grep -q $dag_id" \
    || fail "the S3 DAG bundle never delivered the DAG, or it was never parsed"
  pass "the S3 DAG bundle delivered the DAG and it was parsed"

  docker exec airflow airflow dags unpause "$dag_id" >/dev/null 2>&1
  docker exec airflow airflow dags trigger "$dag_id" >/dev/null 2>&1 \
    || fail "could not trigger the DAG"

  local state=""
  for _ in $(seq 1 30); do
    state=$(docker exec airflow airflow dags list-runs "$dag_id" -o plain 2>/dev/null \
      | grep -E "^$dag_id" | head -1 | tr -s ' ' | cut -d' ' -f3)
    case "$state" in success|failed) break ;; esac
    sleep 10
  done
  [ "$state" = "success" ] || fail "DAG run finished in state ${state:-none}, not success"
  pass "DAG run reached success, so a task really executed"

  docker exec airflow python -c "import boto3; boto3.client('s3', endpoint_url='http://seaweed:8333').delete_object(Bucket='airflow', Key='dags/$dag_id.py')" >/dev/null 2>&1 || true
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
}

# Prometheus: /-/ready answers before the config is loaded, and a scrape config
# an image bump moved looks identical from outside. The matrix runs telemetry on
# its own, so the services it scrapes are absent and 8 of 9 targets are legitimately
# down. Assert what holds alone: the config parsed into targets, the self-scrape
# works, a query returns data, OTLP reaches Prometheus both directly and through
# the collector, and Grafana logs in and queries Prometheus. All of it runs in the
# one grafana/otel-lgtm container.
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

  # The same encoding through the collector's OTLP HTTP receiver, which forwards
  # to Prometheus. This is the path an OpenTelemetry SDK uses by default.
  sed 's/odctl_smoke_total/odctl_smoke_collector_total/' /tmp/odctl-otlp.json > /tmp/odctl-otlp-collector.json
  curl -fsS --max-time 10 -X POST -H "Content-Type: application/json" \
    --data-binary @/tmp/odctl-otlp-collector.json \
    "http://127.0.0.1:4318/v1/metrics" >/dev/null \
    || fail "the OTLP collector rejected a metric on :4318"
  retry 12 5 bash -c '
    curl -fsS --max-time 10 "http://127.0.0.1:19090/api/v1/query?query=odctl_smoke_collector_total" 2>/dev/null \
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
}

# Marquez: the namespaces endpoint answers on an empty database, so it proves
# only that the service started. Lineage is the product, so post a real
# OpenLineage event and read the dataset back out.
smoke_lineage() {
  retry 60 5 http_ok "http://127.0.0.1:5002/api/v1/namespaces" || fail "no HTTP response from :5002"

  local ns="odctl-smoke" run_id="a1b2c3d4-0000-4000-8000-00000000$$"
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

  for event in START COMPLETE; do
    curl -fsS -X POST "http://127.0.0.1:5002/api/v1/lineage" \
      -H 'Content-Type: application/json' \
      -d "{\"eventType\":\"$event\",\"eventTime\":\"$now\",
           \"producer\":\"odctl-smoke\",
           \"run\":{\"runId\":\"$run_id\"},
           \"job\":{\"namespace\":\"$ns\",\"name\":\"smoke-job\"},
           \"outputs\":[{\"namespace\":\"$ns\",\"name\":\"smoke-dataset\"}]}" \
      >/dev/null 2>&1 || fail "Marquez rejected the $event OpenLineage event"
  done
  pass "posted START and COMPLETE OpenLineage events"

  # Marquez writes the job, run and dataset from those events. Reading the
  # dataset back proves it persisted them rather than accepting and dropping.
  retry 12 5 bash -c \
    "curl -fsS 'http://127.0.0.1:5002/api/v1/namespaces/$ns/datasets/smoke-dataset' | grep -q smoke-dataset" \
    || fail "the dataset never appeared, so Marquez did not persist the lineage"
  curl -fsS "http://127.0.0.1:5002/api/v1/namespaces/$ns/jobs/smoke-job" 2>/dev/null \
    | grep -q smoke-job || fail "the job did not read back"
  pass "dataset and job both read back from Marquez"
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

  # The principal domain odctl sets is open-data.local, not the upstream
  # default. A wrong domain fails with a misleading invalid password error.
  local token
  token=$(curl -fsS --max-time 20 -H 'Content-Type: application/json' \
    -d "{\"email\":\"admin@open-data.local\",\"password\":\"$(printf admin | base64)\"}" \
    "http://127.0.0.1:8585/api/v1/users/login" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["accessToken"])' 2>/dev/null)
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

  # A real ingestion. Postgres is already running, so it is its own source.
  curl -fsS --max-time 60 -X DELETE -H "$auth" \
    "http://127.0.0.1:8585/api/v1/services/databaseServices/name/odctl_smoke?hardDelete=true&recursive=true" \
    >/dev/null 2>&1 || true
  local svc
  svc=$(curl -fsS --max-time 30 -X PUT -H "$auth" -H 'Content-Type: application/json' \
    -d '{"name":"odctl_smoke","serviceType":"Postgres","connection":{"config":{"type":"Postgres","scheme":"postgresql+psycopg2","username":"user","authType":{"password":"password"},"hostPort":"postgres:5432","database":"omt"}}}' \
    "http://127.0.0.1:8585/api/v1/services/databaseServices" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' 2>/dev/null)
  [ -n "$svc" ] || fail "could not create a database service"

  local pipe
  pipe=$(curl -fsS --max-time 30 -X POST -H "$auth" -H 'Content-Type: application/json' \
    -d "{\"name\":\"odctl_smoke_metadata\",\"pipelineType\":\"metadata\",\"service\":{\"id\":\"$svc\",\"type\":\"databaseService\"},\"sourceConfig\":{\"config\":{\"type\":\"DatabaseMetadata\"}},\"airflowConfig\":{\"startDate\":\"2026-01-01T00:00:00.000Z\"}}" \
    "http://127.0.0.1:8585/api/v1/services/ingestionPipelines" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' 2>/dev/null)
  [ -n "$pipe" ] || fail "could not create an ingestion pipeline"

  curl -fsS --max-time 90 -X POST -H "$auth" \
    "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/deploy/$pipe" 2>/dev/null \
    | grep -q 'has been created' || fail "the pipeline did not deploy a DAG into Airflow"
  pass "ingestion pipeline deployed a DAG"

  # Airflow's dag_processor has to parse the new file before it can be triggered.
  local triggered=no
  for _ in $(seq 1 24); do
    if curl -fsS --max-time 90 -X POST -H "$auth" \
        "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/trigger/$pipe" 2>/dev/null \
        | grep -q 'has been triggered'; then triggered=yes; break; fi
    sleep 5
  done
  [ "$triggered" = "yes" ] || fail "the pipeline never triggered"

  local state=""
  for _ in $(seq 1 30); do
    state=$(curl -fsS --max-time 15 -H "$auth" \
      "http://127.0.0.1:8585/api/v1/services/ingestionPipelines/name/odctl_smoke.odctl_smoke_metadata?fields=pipelineStatuses" 2>/dev/null \
      | python3 -c 'import json,sys; s=json.load(sys.stdin).get("pipelineStatuses") or []; print(s[0]["pipelineState"] if s else "")' 2>/dev/null)
    case "$state" in success|failed|partialSuccess) break ;; esac
    sleep 10
  done
  [ "$state" = "success" ] || fail "ingestion run finished in state ${state:-none}, not success"
  pass "ingestion run reached success"

  # Elasticsearch moved to 9.3.0 with this upgrade, so assert the catalogue is
  # searchable rather than merely populated.
  curl -fsS --max-time 60 -X POST -H "$auth" \
    "http://127.0.0.1:8585/api/v1/apps/trigger/SearchIndexingApplication" >/dev/null 2>&1
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

  # The 2.0 features the upgrade was for. A 1.13 server has neither.
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

  curl -fsS --max-time 60 -X DELETE -H "$auth" \
    "http://127.0.0.1:8585/api/v1/services/databaseServices/name/odctl_smoke?hardDelete=true&recursive=true" \
    >/dev/null 2>&1 || true
}

# Feast keeps no feature values of its own, so liveness proves nothing here.
# This builds a real Iceberg table through the catalog, registers a feature view
# over it, takes a point-in-time join, materializes to Valkey and reads it back.
# A failure in any of those is a broken profile even when both containers are up.
smoke_feast() {
  retry 60 5 http_ok "http://127.0.0.1:8890/api/v1/projects" || fail "no HTTP response from the feast UI on :8890"
  pass "feast UI answering, registry reachable"

  local work="${TMPDIR:-/tmp}/odctl-feast-smoke"
  rm -rf "$work"; mkdir -p "$work/feature_repo"

  # The offline half runs in the caller's environment, not in the container:
  # the published image carries feast[minimal], which has no iceberg or duckdb.
  uv venv "$work/.venv" >/dev/null 2>&1 || fail "could not create a venv for the feast client"
  VIRTUAL_ENV="$work/.venv" uv pip install -q \
    "feast[duckdb,iceberg,redis,postgres]==0.66.0" "pyarrow" >/dev/null 2>&1 \
    || fail "could not install the feast client"

  # warehouse="" is required. Feast's REST client puts warehouse into the URL
  # path as a prefix for Polaris and Nessie style catalogs, and
  # apache/iceberg-rest-fixture serves the spec with no prefix, so a real
  # warehouse gives HTTP 400 "Ambiguous URI empty segment".
  # A fresh project per run. `feast teardown` leaves rows in
  # feature_view_version_history, so applying the same feature view into the
  # same project twice hits the primary key on
  # (feature_view_name, project_id, version_number) and the second run fails.
  local proj="odctl_smoke_$(date -u +%Y%m%d%H%M%S)"

  cat > "$work/feature_repo/feature_store.yaml" <<YAML
project: ${proj}
provider: local
registry:
  registry_type: sql
  path: postgresql+psycopg://user:password@localhost:5432/feast
offline_store:
  type: duckdb
online_store:
  type: redis
  connection_string: "localhost:6379,username=user,password=password"
entity_key_serialization_version: 3
YAML

  cat > "$work/feature_repo/definitions.py" <<'PYDEF'
from datetime import timedelta
from feast import Entity, FeatureView, Field
from feast.types import Float32
from feast.infra.data_sources.contrib.iceberg_catalog.iceberg_source import IcebergSource

driver = Entity(name="driver", join_keys=["driver_id"])
src = IcebergSource(
    warehouse="", namespace="smoke", table="driver_stats",
    catalog_type="rest", catalog_name="odctl",
    endpoint="http://localhost:8181",
    timestamp_field="event_timestamp",
)
fv = FeatureView(
    name="driver_stats", entities=[driver], ttl=timedelta(days=365),
    schema=[Field(name="conv_rate", dtype=Float32)], source=src, online=True,
)
PYDEF

  cat > "$work/build.py" <<'PYBUILD'
import datetime, pyarrow as pa
from pyiceberg.catalog import load_catalog
cat = load_catalog("odctl")
cat.create_namespace_if_not_exists("smoke")
schema = pa.schema([
    pa.field("driver_id", pa.int64(), nullable=False),
    pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("conv_rate", pa.float32(), nullable=False),
])
try: cat.drop_table("smoke.driver_stats")
except Exception: pass
t = cat.create_table("smoke.driver_stats", schema=schema)
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
t.append(pa.Table.from_pydict({
    "driver_id": [1001, 1002],
    "event_timestamp": [now - datetime.timedelta(hours=1)] * 2,
    "conv_rate": [0.5, 0.75],
}, schema=schema))
print(t.scan().to_arrow().num_rows)
PYBUILD

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

  export PYICEBERG_CATALOG__ODCTL__TYPE=rest
  export PYICEBERG_CATALOG__ODCTL__URI=http://localhost:8181
  export PYICEBERG_CATALOG__ODCTL__WAREHOUSE=s3://warehouse/
  export PYICEBERG_CATALOG__ODCTL__S3__ENDPOINT=http://localhost:8333
  export PYICEBERG_CATALOG__ODCTL__S3__ACCESS_KEY_ID=user
  export PYICEBERG_CATALOG__ODCTL__S3__SECRET_ACCESS_KEY=password
  export PYICEBERG_CATALOG__ODCTL__S3__PATH_STYLE_ACCESS=true
  export PYICEBERG_CATALOG__ODCTL__S3__REGION=us-east-1

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

  run_step "feast apply failed" "$feast_bin" -c feature_repo apply
  pass "feast apply registered the feature view against the catalog"

  run_step "the point-in-time join returned the wrong values" "$py" check.py
  pass "get_historical_features read Iceberg through DuckDB"

  run_step "feast materialize into valkey failed" \
    "$feast_bin" -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"
  run_step "the online read from valkey returned the wrong values" "$py" online.py
  pass "materialize wrote to valkey and get_online_features read it back"

  (cd "$work" && "$feast_bin" -c feature_repo teardown) >/dev/null 2>&1 || true
  curl -fsS --max-time 10 -X DELETE \
    "http://127.0.0.1:8181/v1/namespaces/smoke/tables/driver_stats?purgeRequested=true" >/dev/null 2>&1 || true
  curl -fsS --max-time 10 -X DELETE "http://127.0.0.1:8181/v1/namespaces/smoke" >/dev/null 2>&1 || true
  rm -rf "$work"
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
  deps)       smoke_deps ;;
  postgres|storage|catalog|valkey) smoke_infra ;;
  metabase)   smoke_metabase ;;
  airflow)    smoke_airflow ;;
  mlflow)     smoke_mlflow ;;
  lineage)    smoke_lineage ;;
  telemetry)  smoke_telemetry ;;
  metadata)   smoke_metadata ;;
  fluss)      smoke_fluss ;;
  feast)      smoke_feast ;;
  feast-serve) smoke_http_only "http://127.0.0.1:6566/health" ;;
  *)
    echo "ℹ️  $PROFILE: no functional assertion defined, checking containers only"
    [ "$(docker ps -q | wc -l)" -ge 1 ] || fail "no containers running"
    pass "containers running" ;;
esac
