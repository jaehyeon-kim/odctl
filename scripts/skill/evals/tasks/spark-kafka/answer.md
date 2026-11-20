# spark-kafka

Answer sheet of the case `spark-kafka`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A1 (a step needs an earlier step), A8 (image content assumed).

## Records

- github `jaehyeon-kim/odctl#20`: a user connected to `localhost:29092`, a port Kafka advertised only for minikube.
- planning `architecting-analytics/validation-live-stack.md:146`: the Spark image was assumed to hold a jar it does not.

## Right answer

- Start `odctl up spark-lite kafka-lite` (`docs/snippets/spark/commands.sh`, sections `up` and `up-kafka-lite`). `spark-lite` depends on `catalog` (`registry.yml:122`).
- From a container the bootstrap address is `broker-1:19092`: the `kafka` container has the network aliases `broker-1`, `broker-2` and `broker-3` (`compose-kafka.yml:38-44`), and its internal listener advertises `broker-1:19092` (`compose-kafka.yml:49`, `registry.yml:81`).
- The job runs in the container `spark-master`: `docker cp read_orders.py spark-master:/tmp/`, then `docker exec spark-master /opt/spark/bin/spark-submit /tmp/read_orders.py` (`commands.sh` section `kafka-read`; `smoke.sh` `smoke_spark`, lines 434 to 442).
- No `--packages` option: the Kafka connector is in the shared jar volume (`docs/guides/spark.md:55`).
- The job prints every message: `show()` prints 20 rows unless given a count, so the job passes a count (`show(rows.count(), truncate=False)`) or prints each row another way, such as `collect()` or `toLocalIterator()`. No kind counts a job that prints only 20 rows.

## Wrong answers seen or expected

- `localhost:9092` or `127.0.0.1:9092` inside the container: the external listener advertises `127.0.0.1:9092` for the host (`compose-kafka.yml:49`).
- `kafka:9092`, or any address on port 29092 (removed in 1.1.0, `docs/about/changelog.md:169`).
- `--packages org.apache.spark:spark-sql-kafka...`, which downloads a jar the image already has.
- A container named `spark`; it is `spark-master`.
- `odctl up spark` (no such profile; `odctl up spark kafka-lite --dry-run` exits 1 with `Unknown profiles: spark`).
