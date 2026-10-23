# Produce and consume with Kafka

The `kafka-lite` profile runs one Kafka broker in KRaft mode, the Karapace schema registry, Kafka Connect and Kafka UI. `kafka-full` runs three brokers with the same services beside them. The end-to-end tests run the commands below on every release.

```bash
odctl up kafka-lite
```

| Endpoint                                     | Address                                                                    |
| -------------------------------------------- | -------------------------------------------------------------------------- |
| Bootstrap servers from the host              | `127.0.0.1:9092` (`kafka-full` adds `127.0.0.1:9093` and `127.0.0.1:9094`) |
| Bootstrap servers inside the `odctl` network | `broker-1:19092`                                                           |
| Kafka UI                                     | `http://127.0.0.1:8086`                                                    |
| Schema registry (Karapace)                   | `http://127.0.0.1:8081`                                                    |
| Kafka Connect REST API                       | `http://127.0.0.1:8083`                                                    |

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

The consumer reads through a consumer group, so its offsets are stored in the broker's `__consumer_offsets` topic.

Kafka UI at `http://127.0.0.1:8086` shows the topics, their messages, the consumer groups and the schemas in Karapace.

## Keep messages longer

The brokers delete old messages. A partition keeps data for one day or up to 500 MB, and a segment is deleted once either limit is passed. The compose file sets both: `KAFKA_LOG_RETENTION_MS` is `86400000` and `KAFKA_LOG_RETENTION_BYTES` is `524288000`. A topic created without settings takes these values:

```bash
docker exec kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server broker-1:19092 \
  --describe --all --entity-type topics --entity-name demo | grep -E '^ *retention\.(ms|bytes)='
```

The output shows `retention.ms=86400000` and `retention.bytes=524288000`. To keep everything in one topic, set `retention.ms` and `retention.bytes` to `-1` when you create it. `-1` means no limit. Other topics keep the broker defaults.

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic history --partitions 1 --replication-factor 1 \
  --config retention.ms=-1 --config retention.bytes=-1

docker exec kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server broker-1:19092 \
  --describe --entity-type topics --entity-name history
```

The describe command lists the settings of that topic: `retention.ms=-1` and `retention.bytes=-1`. `retention.bytes` applies to each partition, so a topic with three partitions at 500 MB can hold 1.5 GB. To change an existing topic, use `kafka-configs.sh --alter --add-config` with the same two settings. If older messages are missing, see [Troubleshooting](https://jaehyeon.me/odctl/latest/troubleshooting/#older-messages-are-missing).

## Kafka Connect

Both Kafka profiles run a Kafka Connect worker beside the brokers. [Kafka Connect](https://jaehyeon.me/odctl/latest/guides/kafka-connect/index.md) lists the plugins it loads and shows how to register a connector.
