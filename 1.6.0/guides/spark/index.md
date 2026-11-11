# Spark

The `spark-lite` profile runs a Spark master, one worker and the Spark History Server. `spark-full` runs three workers. Spark's default catalog is `iceberg`, already pointed at the Iceberg REST catalog, so `spark-sql` reads and writes Iceberg tables with no extra settings. The end-to-end tests run the commands below on every release.

This guide builds on [Kafka](https://jaehyeon.me/odctl/latest/guides/kafka/index.md), which writes and reads a topic, and [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/index.md), whose Avro records the last step reads. Start the profile:

```bash
odctl up spark-lite
```

| Endpoint                                        | Address                      |
| ----------------------------------------------- | ---------------------------- |
| Spark master UI from the host                   | `http://127.0.0.1:9080`      |
| Master URL from the host                        | `spark://127.0.0.1:7077`     |
| Spark History Server from the host              | `http://127.0.0.1:18080`     |
| Master URL inside the `odctl` network           | `spark://spark-master:7077`  |
| Spark History Server inside the `odctl` network | `http://spark-history:18080` |

## Run SQL Against Iceberg

This creates a namespace and a table in the `iceberg` catalog, inserts three rows and counts them:

```bash
docker exec spark-master /opt/spark/bin/spark-sql -e "
  CREATE NAMESPACE IF NOT EXISTS iceberg.demo;
  CREATE OR REPLACE TABLE iceberg.demo.t (id BIGINT) USING iceberg;
  INSERT INTO iceberg.demo.t VALUES (1),(2),(3);
  SELECT count(*) FROM iceberg.demo.t;"
```

The query prints `3`. The table is in the same catalog that Flink, Kafka Connect and Trino use, and [Ingest into Iceberg](https://jaehyeon.me/odctl/latest/guides/iceberg-ingestion/index.md) shows the other engines writing to it.

## See Finished Applications

Every Spark application writes an event log to `/tmp/spark-events`, which all Spark containers share. This lists the logs:

```bash
docker exec spark-master ls /tmp/spark-events
```

The command prints one name per application, such as `eventlog_v2_local-1792817297659`. The Spark History Server at `http://127.0.0.1:18080` reads the same directory, so the `spark-sql` run above appears there after it ends, with its jobs, stages and SQL plans. The master UI at `http://127.0.0.1:9080` shows the workers and the applications the master has run.

The event logs are on a volume held in memory, so [`odctl down`](https://jaehyeon.me/odctl/latest/how-it-works/#where-data-lives) removes them.

The History Server lists the `spark-sql` run:

The master UI at `http://127.0.0.1:9080` lists the worker:

## Read a Kafka Topic

The Kafka connector for Spark is in the shared volume with its dependencies, so a job reads Kafka with no `--packages` option. Start `kafka-lite` beside Spark:

```bash
odctl up kafka-lite
```

This creates the topic `spark-demo` and writes three messages to it:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --topic spark-demo --partitions 1 --replication-factor 1

for i in 1 2 3; do echo "{\"n\":$i}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic spark-demo
```

Save this PySpark job as `read_kafka.py`. A batch read with `spark.read` reads the topic from its first offset to its last and then ends:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("read-kafka").getOrCreate()

df = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:19092")
    .option("subscribe", "spark-demo")
    .load()
)
df.selectExpr("CAST(value AS STRING) AS value").orderBy("value").show(truncate=False)
```

Copy the file into the master container and submit it:

```bash
docker cp read_kafka.py spark-master:/tmp/read_kafka.py
docker exec spark-master /opt/spark/bin/spark-submit /tmp/read_kafka.py
```

The job prints a table with the values `{"n":1}`, `{"n":2}` and `{"n":3}`. Kafka returns each message as binary `key` and `value` columns, with the `topic`, `partition`, `offset`, `timestamp` and `timestampType` beside them.

## Read Avro Records Written with the Schema Registry

The `orders` topic that [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/#run-the-sql) fills holds Avro records written with the Karapace schema registry. Each value is a zero byte, the 4-byte id of the schema, and then the record in Avro's binary encoding, so Spark cannot read it as text. Save this job as `read_avro.py`. It gets the latest schema of the subject `orders-value` from Karapace, drops the 5 bytes and decodes the rest with `from_avro`, which needs no `--packages` option because the Avro module is in the shared volume. This works when all records were written with the subject's latest schema version. If the Flink section has not run, the job stops with `HTTP Error 404: Not Found`, because the subject does not exist yet.

```python
import json
import urllib.request

from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import expr

spark = SparkSession.builder.appName("read-avro").getOrCreate()

# The latest schema of the subject, as the schema registry holds it.
url = "http://karapace:8081/subjects/orders-value/versions/latest"
with urllib.request.urlopen(url, timeout=30) as reply:
    schema = json.load(reply)["schema"]

raw = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:19092")
    .option("subscribe", "orders")
    .load()
)

# Skip the first 5 bytes of each value: a zero byte and the 4-byte schema id.
orders = raw.select(
    from_avro(expr("substring(value, 6, length(value) - 5)"), schema).alias("order")
).select("order.*")
orders.orderBy("supplier", "price").show()
```

Copy the file into the master container and submit it:

```bash
docker cp read_avro.py spark-master:/tmp/read_avro.py
docker exec spark-master /opt/spark/bin/spark-submit /tmp/read_avro.py
```

The job prints a table with the columns `supplier` and `price`, and the rows `a` 5.0, `a` 10.0 and `b` 7.5.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), submit applications to `spark://spark-master:7077`. Spark's settings, including the catalog and S3 access to SeaweedFS, are in `spark/spark-defaults.conf` in the workspace.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It runs the Iceberg and Kafka steps above with a table and a topic of its own for each run, and writes the PySpark job into the master container itself:

```bash
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
```

It prints `3`, `Created topic` with the topic's name, and a table with the values `{"n":1}`, `{"n":2}` and `{"n":3}`.
