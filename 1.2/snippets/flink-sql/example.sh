#!/usr/bin/env bash
# Starts flink-lite and kafka-lite, writes three Avro records to a Kafka topic
# with Flink SQL, sums them by supplier into PostgreSQL and prints the result.
# Each run uses its own topic and table names, so the file can run again.
set -euo pipefail

odctl up flink-lite kafka-lite

# Karapace answers its health check before it can store a schema, so wait
# until it accepts one.
until curl -fs -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
  -d '{"schema": "{\"type\": \"string\"}"}' http://127.0.0.1:8081/subjects/ready/versions >/dev/null; do
  sleep 5
done

run=$(date +%s)
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic "orders-$run" --partitions 1 --replication-factor 1
docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE supplier_stats_$run (supplier TEXT PRIMARY KEY, orders BIGINT, total DOUBLE PRECISION);"

docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<SQL | grep -E 'ERROR|Exception' || true
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
CREATE TABLE orders (supplier STRING, price DOUBLE) WITH ('connector'='kafka','topic'='orders-$run','properties.bootstrap.servers'='broker-1:19092','scan.startup.mode'='earliest-offset','scan.bounded.mode'='latest-offset','format'='avro-confluent','avro-confluent.url'='http://karapace:8081');
INSERT INTO orders VALUES ('a', 10.0), ('a', 5.0), ('b', 7.5);
CREATE TABLE stats (supplier STRING, orders BIGINT, total DOUBLE, PRIMARY KEY (supplier) NOT ENFORCED) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='supplier_stats_$run','username'='user','password'='password');
INSERT INTO stats SELECT supplier, COUNT(*), SUM(price) FROM orders GROUP BY supplier;
SQL

docker exec postgres psql -U user -d odctl -c "SELECT * FROM supplier_stats_$run ORDER BY supplier"
