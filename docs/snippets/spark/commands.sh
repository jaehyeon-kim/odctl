# Commands from docs/guides/spark.md. .github/scripts/smoke.sh runs each section.

# --8<-- [start:run-sql]
docker exec spark-master /opt/spark/bin/spark-sql -e "
  CREATE NAMESPACE IF NOT EXISTS iceberg.demo;
  CREATE OR REPLACE TABLE iceberg.demo.t (id BIGINT) USING iceberg;
  INSERT INTO iceberg.demo.t VALUES (1),(2),(3);
  SELECT count(*) FROM iceberg.demo.t;"
# --8<-- [end:run-sql]

# --8<-- [start:event-logs]
docker exec spark-master ls /tmp/spark-events
# --8<-- [end:event-logs]

# --8<-- [start:kafka-topic]
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic spark-demo --partitions 1 --replication-factor 1

for i in 1 2 3; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic spark-demo
# --8<-- [end:kafka-topic]

# --8<-- [start:kafka-read]
docker cp read_kafka.py spark-master:/tmp/read_kafka.py
docker exec spark-master /opt/spark/bin/spark-submit /tmp/read_kafka.py
# --8<-- [end:kafka-read]

# --8<-- [start:avro-read]
docker cp read_avro.py spark-master:/tmp/read_avro.py
docker exec spark-master /opt/spark/bin/spark-submit /tmp/read_avro.py
# --8<-- [end:avro-read]
