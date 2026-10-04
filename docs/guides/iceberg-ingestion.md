# Ingest into Iceberg

Kafka Connect, Flink and Spark all write Iceberg tables through the same REST catalog, `http://catalog:8181`, with the files on SeaweedFS under `s3://warehouse`. The commands below come from the end-to-end tests, which run them on every release, with the names changed.

## Kafka Connect sink

`kafka-lite` does not start the catalog, so start both:

```bash
odctl up kafka-lite catalog
```

Create a namespace and a table through the catalog's REST API:

```bash
api=http://127.0.0.1:8181/v1/namespaces
curl -X POST -H 'Content-Type: application/json' -d '{"namespace":["demo"]}' "$api"
curl -X POST -H 'Content-Type: application/json' \
  -d '{"name":"kc","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"id","required":false,"type":"long"},{"id":2,"name":"name","required":false,"type":"string"}]}}' \
  "$api/demo/tables"
```

Create the topic and the sink's control topic, then write some JSON records:

```bash
for topic in demo-iceberg control-iceberg; do
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
    --create --if-not-exists --topic "$topic" --partitions 1 --replication-factor 1
done
for i in 1 2 3 4 5; do echo "{\"id\":$i,\"name\":\"n$i\"}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic demo-iceberg
```

Register the sink:

```bash
curl -X POST -H 'Content-Type: application/json' http://127.0.0.1:8083/connectors -d '{
  "name": "demo-iceberg",
  "config": {
    "connector.class": "org.apache.iceberg.connect.IcebergSinkConnector",
    "tasks.max": "1",
    "topics": "demo-iceberg",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "iceberg.tables": "demo.kc",
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
  }}'
```

The first commit can take a minute or more, because the sink waits for its control consumer to join a group. After that, `curl $api/demo/tables/kc` shows a snapshot whose summary has `"total-records": "5"`.

## Flink SQL

```bash
odctl up flink-lite
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
```

```sql
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG ice WITH ('type'='iceberg','catalog-type'='rest','uri'='http://catalog:8181','warehouse'='s3://warehouse','s3.endpoint'='http://seaweed:8333','s3.path-style-access'='true','s3.access-key-id'='user','s3.secret-access-key'='password');
CREATE DATABASE IF NOT EXISTS ice.demo_flink;
CREATE TABLE ice.demo_flink.t (id BIGINT, name STRING);
INSERT INTO ice.demo_flink.t VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT COUNT(*) FROM ice.demo_flink.t;
```

## Spark SQL

Spark's default catalog is `iceberg`, already pointed at the REST catalog.

```bash
odctl up spark-lite
docker exec spark-master /opt/spark/bin/spark-sql -e "
  CREATE NAMESPACE IF NOT EXISTS iceberg.demo;
  CREATE OR REPLACE TABLE iceberg.demo.t (id BIGINT) USING iceberg;
  INSERT INTO iceberg.demo.t VALUES (1),(2),(3);
  SELECT count(*) FROM iceberg.demo.t;"
```

Every engine sees the same tables, so a table written by one can be read by the others, and by Trino through its `iceberg` catalog.
