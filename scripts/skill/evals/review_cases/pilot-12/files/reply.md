I wrote the two files below, but couldn't run them: Docker isn't available on this machine, so `odctl up` stopped with "Docker is not reachable". All I could check was that the files are valid (`bash -n run.sh`, Python compile of `read_orders.py`) and that `odctl up kafka-lite spark-lite --dry-run` plans the right profiles. The first real run will be on your laptop.

## Files

**read_orders.py** is the PySpark job. It does a one-off (batch) read of the `orders` topic from the earliest to the latest offset of every partition. It turns the key and value into strings and prints one line per message with partition, offset, timestamp, key and value, in order. It ends with a count and then exits.
- It connects to `broker-1:19092`, the broker's address inside the odctl Docker network. That address works with both `kafka-lite` and `kafka-full`.
- You can change the broker or topic with the environment variables `KAFKA_BOOTSTRAP` and `KAFKA_TOPIC`.

**run.sh** does three things:
1. Runs `odctl up kafka-lite spark-lite`, which returns once every service is healthy. `spark-lite` also starts `deps`, `postgres`, `storage` and `catalog`.
2. Copies `read_orders.py` into the `spark-master` container with `docker cp`. The Spark containers don't mount your folder, so the copy is needed.
3. Runs the job there with `spark-submit --master spark://spark-master:7077`. It sets `spark.driver.host=spark-master` so the worker can connect back to the job.

Run it with `./run.sh`.

## Before you run it

- **odctl and Docker:** the script calls `odctl` from your PATH; set `ODCTL=/path/to/odctl` to use another copy. Docker must be running, because the script uses `docker cp` and `docker exec`.
- **No extra downloads:** odctl's `deps` profile already puts the Spark Kafka connector jars on the Spark classpath, so there's no `--packages` and nothing is fetched when the job starts.
- **What gets printed:** the job prints only what's in the topic when it starts, then exits. It doesn't keep watching for new messages. Every message goes to your terminal, so a very large topic means a lot of output.
- **The topic must have data:** this script doesn't create `orders` or write anything to it. Produce some messages first, for example from the Kafka UI at http://127.0.0.1:8086 or to `127.0.0.1:9092` from your laptop. If the topic doesn't exist, the read either fails or prints `Read 0 message(s)`.
- **Text messages:** key and value are printed as UTF-8 text. If `orders` holds Avro from the Schema Registry, the values will print as unreadable text.
- **Bigger clusters:** to use the 3-broker or 3-worker clusters, run `KAFKA_PROFILE=kafka-full SPARK_PROFILE=spark-full ./run.sh`. Don't start the `-lite` and `-full` version of the same tool together.
- **Port clashes:** the stack publishes many ports on 127.0.0.1, including 9092, 7077, 9080, 8081, 8083, 8086, 5432, 8333 and 8181. Anything else on your laptop using one of them will make `odctl up` fail.
- **Stopping it:** `odctl down kafka-lite spark-lite` stops these two profiles but not the ones they started (`deps`, `postgres`, `storage`, `catalog`). `odctl down --all` stops everything. Stopping deletes the topic's data, because it's kept inside the containers.
