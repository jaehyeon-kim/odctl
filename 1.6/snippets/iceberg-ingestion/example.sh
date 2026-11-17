#!/usr/bin/env bash
# Starts kafka-lite and flink-lite, which starts the catalog, then writes five
# rows to an Iceberg table through the Kafka Connect sink and three rows to
# another through Flink SQL, and prints both counts. Each run uses its own
# topic, connector and table names, so the file can run again.
set -euo pipefail

odctl up kafka-lite flink-lite

run=$(date +%s)
api=http://127.0.0.1:8181/v1/namespaces
until curl -fs http://127.0.0.1:8083/connectors >/dev/null; do sleep 2; done

# A namespace, which may exist already, and an empty table for the sink.
curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -d '{"namespace":["demo"]}' "$api"
curl -fs -o /dev/null -X POST -H 'Content-Type: application/json' \
  -d "{\"name\":\"kc_$run\",\"schema\":{\"type\":\"struct\",\"schema-id\":0,\"fields\":[{\"id\":1,\"name\":\"id\",\"required\":false,\"type\":\"long\"},{\"id\":2,\"name\":\"name\",\"required\":false,\"type\":\"string\"}]}}" \
  "$api/demo/tables"

# Create the topic and the sink's control topic, then write five JSON records.
for topic in "iceberg-$run" "control-$run"; do
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
    --create --topic "$topic" --partitions 1 --replication-factor 1
done
for i in 1 2 3 4 5; do echo "{\"id\":$i,\"name\":\"n$i\"}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic "iceberg-$run"

curl -fs -o /dev/null -X POST -H 'Content-Type: application/json' http://127.0.0.1:8083/connectors -d @- <<JSON
{
  "name": "iceberg-$run",
  "config": {
    "connector.class": "org.apache.iceberg.connect.IcebergSinkConnector",
    "tasks.max": "1",
    "topics": "iceberg-$run",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "iceberg.tables": "demo.kc_$run",
    "iceberg.control.topic": "control-$run",
    "iceberg.control.commit.interval-ms": "10000",
    "iceberg.kafka.session.timeout.ms": "300000",
    "iceberg.kafka.heartbeat.interval.ms": "3000",
    "iceberg.kafka.auto.offset.reset": "earliest",
    "consumer.override.auto.offset.reset": "earliest",
    "iceberg.catalog.type": "rest",
    "iceberg.catalog.uri": "http://catalog:8181",
    "iceberg.catalog.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
    "iceberg.catalog.client.region": "us-east-1",
    "iceberg.catalog.s3.endpoint": "http://seaweed:8333",
    "iceberg.catalog.s3.path-style-access": "true",
    "iceberg.catalog.s3.access-key-id": "user",
    "iceberg.catalog.s3.secret-access-key": "password"
  }
}
JSON

# The first commit can take a minute or more.
until curl -s "$api/demo/tables/kc_$run" | grep '"total-records":"5"' >/dev/null; do sleep 5; done
echo "demo.kc_$run: 5 records written by the Kafka Connect sink"
curl -s -o /dev/null -X DELETE "http://127.0.0.1:8083/connectors/iceberg-$run"

docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<SQL | grep -E '^[|+]'
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG ice WITH ('type'='iceberg','catalog-type'='rest','uri'='http://catalog:8181','warehouse'='s3://warehouse','s3.endpoint'='http://seaweed:8333','s3.path-style-access'='true','s3.access-key-id'='user','s3.secret-access-key'='password');
CREATE DATABASE IF NOT EXISTS ice.demo_flink;
CREATE TABLE ice.demo_flink.t_$run (id BIGINT, name STRING);
INSERT INTO ice.demo_flink.t_$run VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT COUNT(*) AS flink_rows FROM ice.demo_flink.t_$run;
SQL
