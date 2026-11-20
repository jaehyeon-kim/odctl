# Reply

I wrote `read_orders.py` and `run.sh`. I have not run either one: Docker isn't available on this machine. I checked that `run.sh` parses (`bash -n`), that `read_orders.py` compiles, and that `odctl up kafka-lite spark-lite --dry-run` produces a plan.

## Files

- **`read_orders.py`** is the PySpark job.
  - It does a batch read of the `orders` topic from the earliest to the latest offset. That offset range is fixed when the job starts.
  - It prints the message count, then every message with partition, offset, timestamp, key and value. Key and value are cast to strings, and the rows are sorted by partition and offset.
  - It connects to `broker-1:19092`, the broker address on the `odctl` Docker network. You can override the address and topic with the `KAFKA_BOOTSTRAP` and `KAFKA_TOPIC` environment variables.
- **`run.sh`** does three things:
  1. It runs `py/bin/odctl up kafka-lite spark-lite`. `spark-lite` also starts catalog, deps, postgres and storage. The `deps` profile puts the Spark Kafka connector jars on Spark's classpath, so the job needs no `--packages`.
  2. It copies the job into the `spark-master` container.
  3. It runs `spark-submit` there against `spark://spark-master:7077`, with 512m for the driver and 512m for the executor.

## Before you run it

- Run `./run.sh` on your laptop, which needs Docker. The first run pulls images and can take a while.
- `kafka-lite` does not create the `orders` topic or put any messages in it. If the topic doesn't exist, the job fails with an unknown-topic error. If it is empty, the job prints `0 message(s)`. Create and fill the topic first, for example from the Kafka UI at http://127.0.0.1:8086.
- The job reads a snapshot and then exits. It does not wait for new messages. If you want that, it would need to be a streaming job instead.
- Values are shown as text. If your messages are Avro or another binary format, they will look garbled.
- `run.sh` finds odctl at `py/bin/odctl` next to the script. Set `ODCTL=/path/to/odctl` to use a different install.
- The script leaves the stack running afterwards. Stop it with `py/bin/odctl down spark-lite kafka-lite`. Add `--volumes` if you also want the volumes removed.
