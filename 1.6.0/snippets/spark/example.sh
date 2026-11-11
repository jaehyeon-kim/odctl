#!/usr/bin/env bash
# Starts spark-lite and kafka-lite, writes and counts an Iceberg table with
# spark-sql, then writes three messages to a topic and reads them with a
# PySpark batch job. Each run uses its own table and topic names.
set -euo pipefail

odctl up spark-lite kafka-lite

run=$(date +%s)
docker exec spark-master /opt/spark/bin/spark-sql -e "
  CREATE NAMESPACE IF NOT EXISTS iceberg.demo;
  CREATE TABLE iceberg.demo.t_$run (id BIGINT) USING iceberg;
  INSERT INTO iceberg.demo.t_$run VALUES (1),(2),(3);
  SELECT count(*) FROM iceberg.demo.t_$run;" 2>/dev/null

docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic "spark-$run" --partitions 1 --replication-factor 1
for i in 1 2 3; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic "spark-$run"

docker exec -i spark-master sh -c "cat > /tmp/read_kafka_$run.py" <<PY
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("read-kafka").getOrCreate()
df = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:19092")
    .option("subscribe", "spark-$run")
    .load()
)
df.selectExpr("CAST(value AS STRING) AS value").orderBy("value").show(truncate=False)
PY
docker exec spark-master /opt/spark/bin/spark-submit "/tmp/read_kafka_$run.py" 2>/dev/null
