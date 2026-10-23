# Commands from docs/guides/kafka.md. .github/scripts/smoke.sh runs each section.

# --8<-- [start:create-topic]
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic demo --partitions 1 --replication-factor 1
# --8<-- [end:create-topic]

# --8<-- [start:produce-consume]
for i in 1 2 3 4 5; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic demo

docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic demo --from-beginning --max-messages 5 --timeout-ms 60000
# --8<-- [end:produce-consume]

# --8<-- [start:retention-default]
docker exec kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server broker-1:19092 \
  --describe --all --entity-type topics --entity-name demo | grep -E '^ *retention\.(ms|bytes)='
# --8<-- [end:retention-default]

# --8<-- [start:retention-unlimited]
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic history --partitions 1 --replication-factor 1 \
  --config retention.ms=-1 --config retention.bytes=-1

docker exec kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server broker-1:19092 \
  --describe --entity-type topics --entity-name history
# --8<-- [end:retention-unlimited]
