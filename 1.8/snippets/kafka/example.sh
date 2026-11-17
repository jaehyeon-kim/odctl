#!/usr/bin/env bash
# Starts kafka-lite, creates the topic demo, writes five records and reads them back.
set -euo pipefail

odctl up kafka-lite

docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --if-not-exists --topic demo --partitions 1 --replication-factor 1

for i in 1 2 3 4 5; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic demo

docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic demo --from-beginning --max-messages 5 --timeout-ms 60000
