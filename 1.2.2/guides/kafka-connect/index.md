# Kafka Connect

Both Kafka profiles run one Kafka Connect worker, `connect`, beside the brokers. Kafka Connect runs connectors: a source connector writes records from another system into Kafka, and a sink connector writes records from Kafka into another system. The worker loads its connectors from the shared volume that the `deps` profile fills, and you manage them through its REST API. The end-to-end tests run the commands below on every release.

This guide builds on [Kafka](https://jaehyeon.me/odctl/latest/guides/kafka/index.md), which starts `kafka-lite` and reads a topic with the console consumer.

Start the profile:

```bash
odctl up kafka-lite
```

| Setting                             | Value                                  |
| ----------------------------------- | -------------------------------------- |
| REST API from the host              | `http://127.0.0.1:8083`                |
| REST API inside the `odctl` network | `http://connect:8083`                  |
| Plugin folder                       | `/mnt/shared-deps/connect`             |
| Default converters                  | JSON with schemas, for keys and values |
| Offset flush interval               | 10 seconds                             |

The converters and the flush interval are set today in the `connect` service of `.odctl/compose-kafka.yml` (`offset.flush.interval.ms=10000`), where an edit can change them.

## Plugins

The `deps` image puts these connectors in the plugin folder: the Apache Iceberg sink, the Debezium PostgreSQL source, the ClickHouse sink, the Aiven JDBC connector, the Aiven S3 sink, the Redis connector and the MSK data generator. This lists the classes Connect has loaded:

```bash
curl -s http://127.0.0.1:8083/connector-plugins
```

The reply is a JSON list with one entry per class. The tests check that it includes `org.apache.iceberg.connect.IcebergSinkConnector`, `io.debezium.connector.postgresql.PostgresConnector` and `com.clickhouse.kafka.connect.ClickHouseSinkConnector`. A plugin missing from the volume does not stop Connect from starting. It only leaves the class out of this list.

## Register a Connector

A connector is a name and a `config` object, posted to `/connectors`. The MSK data generator is a source connector that needs nothing but Kafka: it writes made-up records to a topic. Save this configuration as `demo-datagen.json`. It writes a record to the topic `customers` every half second, with an ISBN-10 number as its key, a first name and a number of visits from 1 to 10:

```json
{
  "name": "demo-datagen",
  "config": {
    "connector.class": "com.amazonaws.mskdatagen.GeneratorSourceConnector",
    "tasks.max": "1",
    "genkp.customers.with": "#{Code.isbn10}",
    "genv.customers.name.with": "#{Name.first_name}",
    "genv.customers.visits.with": "#{number.number_between '1','10'}",
    "global.throttle.ms": "500",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false"
  }
}
```

The worker's default converters expect JSON with a schema envelope, so the connector sets its own: plain strings for keys, and JSON without a schema for values. Post the file from the folder that holds it:

```bash
curl -X POST -H 'Content-Type: application/json' \
  http://127.0.0.1:8083/connectors -d @demo-datagen.json
```

The reply repeats the configuration, with `"tasks":[]` and `"type":"source"`. The worker starts the task right after it answers.

## Read Its Records

The broker creates `customers` when the connector first writes to it, because automatic topic creation is on by default. This reads the first three records with their keys:

```bash
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic customers --from-beginning --max-messages 3 --timeout-ms 60000 \
  --formatter-property print.key=true
```

Each line is a key, a tab and a value such as `{"name":"Patrina","visits":"3"}`. The names and numbers are random. The consumer ends with `Processed a total of 3 messages`.

## Check and Remove It

This reads the connector's status, then deletes it:

```bash
curl -s http://127.0.0.1:8083/connectors/demo-datagen/status
curl -X DELETE http://127.0.0.1:8083/connectors/demo-datagen
```

The status shows `"state":"RUNNING"` for the connector and for task `0`. A failed task shows `FAILED` with its error. The worker's log has the rest:

```bash
docker logs --tail 40 connect
```

After the delete, the last lines of the log say that the worker stopped the task of `demo-datagen`. Kafka UI at `http://127.0.0.1:8086` lists the registered connectors under Kafka Connect, Connectors. [Ingest into Iceberg](https://jaehyeon.me/odctl/latest/guides/iceberg-ingestion/#kafka-connect-sink) registers a sink connector, the Iceberg sink.

## PostgreSQL for Debezium

The `postgres` profile runs PostgreSQL with `wal_level=logical`. Its init script creates the `cdc` schema and the `cdc_pub` publication for every table in that schema, so a Debezium source can read changes to tables you create in `cdc`. Start both profiles to use it:

```bash
odctl up postgres kafka-lite
```

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), the REST API is `http://connect:8083`, and connectors reach the brokers at `broker-1:19092`, the catalog at `http://catalog:8181` and SeaweedFS at `http://seaweed:8333`.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It holds the configuration above, so it needs no other file:

```bash
#!/usr/bin/env bash
# Starts kafka-lite, registers a data generator connector, reads three of its
# records, prints the connector's status and removes it.
set -euo pipefail

odctl up kafka-lite

# The REST API answers a little after the worker starts.
until curl -fs http://127.0.0.1:8083/connectors >/dev/null; do sleep 2; done

curl -s -X POST -H 'Content-Type: application/json' http://127.0.0.1:8083/connectors -d @- <<'JSON'
{
  "name": "demo-datagen",
  "config": {
    "connector.class": "com.amazonaws.mskdatagen.GeneratorSourceConnector",
    "tasks.max": "1",
    "genkp.customers.with": "#{Code.isbn10}",
    "genv.customers.name.with": "#{Name.first_name}",
    "genv.customers.visits.with": "#{number.number_between '1','10'}",
    "global.throttle.ms": "500",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false"
  }
}
JSON
echo

docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic customers --from-beginning --max-messages 3 --timeout-ms 60000 \
  --formatter-property print.key=true

curl -s http://127.0.0.1:8083/connectors/demo-datagen/status
echo
curl -s -X DELETE http://127.0.0.1:8083/connectors/demo-datagen
```

It prints the reply to the registration, three records, `Processed a total of 3 messages` and the status with `"state":"RUNNING"`.
