I wrote two files.

- `read_orders.py` reads every message of `orders` from the start and prints each key and value.
- `run.sh` starts `spark-lite` and `kafka-lite`, waits until the broker answers, copies the job into `spark-master` and submits it.

The Spark image does not include the Kafka connector, so `spark-submit` loads it with `--packages`, which needs network access the first time.
