# Read the `orders` Kafka topic with PySpark on odctl

## What I wrote

- **`read_orders.py`**: a PySpark batch job. It reads the `orders` topic from the earliest retained offset to the latest offset at start, then prints every message as a table with `partition`, `offset`, `timestamp`, `key` and `value`, plus a count line. It connects to `broker-1:19092`, the kafka-lite broker's internal listener on the odctl network.
- **`run.sh`**: starts what the job needs and runs it.
  1. `py/bin/odctl up kafka-lite spark-lite`. This starts `kafka-lite` and `spark-lite`, plus their dependencies (`deps`, `catalog`, `postgres`, `storage`). I checked the plan with `odctl up --dry-run`, and it lists those profiles.
  2. `docker cp` copies `read_orders.py` into the `spark-master` container.
  3. `docker exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 ...` runs the job on the stack's Spark cluster.

  Run it with `./run.sh`. It uses `py/bin/odctl` next to the script. Set `ODCTL=/path/to/odctl` to use another binary.

## Before you run it

- **I could not run this.** Docker is not available on this machine, so I did not start the stack or submit the job. `run.sh` passes `bash -n`, and `read_orders.py` parses. Nothing has been checked against a live broker or Spark cluster.
- **The topic must exist and have messages.** I did not create or produce to `orders`. The job reads only what Kafka still retains. kafka-lite keeps messages for 24 hours (`KAFKA_LOG_RETENTION_MS=86400000`). If the topic is missing, the read fails.
- **The Kafka connector comes from the `deps` profile.** The odctl source includes `fetch_spark_dependencies.sh`, which downloads `spark-sql-kafka`, `kafka-clients` and `commons-pool2` into the shared Spark classpath. I read this from the odctl package, not from the deps image itself. So the job uses no `--packages` flag. If the job fails with `ClassNotFoundException` for a Kafka class, this is the first place to look.
- **Memory settings are my estimate, not measured.** `spark-master` has a 1 GB container limit, so the driver runs with `--driver-memory 512m`. Executors get `--executor-memory 1g`, which fits the 1500 MB worker. Adjust these if the job is killed or fails.
- **`failOnDataLoss` is off.** Retention can delete old segments while a batch read runs, and the job should not abort for that. Messages deleted that way are simply not printed.
- **Output is large for large topics.** The job prints every message, so a big topic produces a big log. Pipe `./run.sh` to a file if needed.
- **Stopping the stack is manual.** `run.sh` leaves the stack running. Stop it with `py/bin/odctl down kafka-lite spark-lite`. Add `--volumes` only if you want to remove the Spark event-log volume too.
- **Watch the job in the Spark UI.** The master UI is at http://127.0.0.1:9080, and the history server is at http://127.0.0.1:18080.
- **I did not check where odctl writes its workspace.** `run.sh` runs `odctl up` from this folder, so it may create an `.odctl/` workspace here. I did not confirm this, because I did not want to write into the folder while testing.
