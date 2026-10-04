# Produce and consume with Kafka

The `kafka-lite` profile runs one Kafka broker in KRaft mode, the Karapace schema registry, Kafka Connect and Kafka UI. `kafka-full` runs three brokers with the same services beside them. The commands below come from the end-to-end tests, with the names changed.

```bash
odctl up kafka-lite
```

| Endpoint | Address |
| --- | --- |
| Bootstrap servers from the host | `127.0.0.1:9092` (`kafka-full` adds `127.0.0.1:9093` and `127.0.0.1:9094`) |
| Bootstrap servers inside the `odctl` network | `broker-1:19092` |
| Kafka UI | `http://127.0.0.1:8086` |
| Schema registry (Karapace) | `http://127.0.0.1:8081` |
| Kafka Connect REST API | `http://127.0.0.1:8083` |

Port 29092 is a listener for minikube. It advertises `host.minikube.internal`, which does not resolve on a normal host, so a client connects and then fails to produce. Use `127.0.0.1:9092` from the host.

## Create a topic

The Kafka command-line tools are in the broker container, which is `kafka` in `kafka-lite` and `kafka-1` in `kafka-full`:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic demo --partitions 1 --replication-factor 1
```

## Produce and consume

```bash
for i in 1 2 3 4 5; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic demo

docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic demo --from-beginning --max-messages 5 --timeout-ms 60000
```

The consumer reads through a consumer group, so its offsets are stored in the broker's `__consumer_offsets` topic. Kafka UI shows the topic, its messages and the consumer groups.

## Kafka Connect plugins

Connect loads its plugins from the shared volume that the `deps` profile fills. List what it has loaded:

```bash
curl -s http://127.0.0.1:8083/connector-plugins
```

The list includes `org.apache.iceberg.connect.IcebergSinkConnector`, `io.debezium.connector.postgresql.PostgresConnector` and `com.clickhouse.kafka.connect.ClickHouseSinkConnector`, which the tests check on every release. [Ingest into Iceberg](iceberg-ingestion.md) registers the Iceberg sink.
