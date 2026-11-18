# spark-valkey-totals

Answer sheet of the case `spark-valkey-totals`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address or login from the wrong side, or guessed), A8 (stack setting or image content assumed).

## Records

- github `jaehyeon-kim/odctl#20` and planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the wrong side (A3).
- planning `architecting-analytics/validation-live-stack.md:146` and `odctl/release/1.2.0/review-batch1.md:12` (R1 2): what the Spark image holds was assumed (A8).

## Right answer

- `odctl up spark-full valkey` if anything is not running (`registry.yml:122`, `153`).
- Inside the `odctl` network Valkey is `valkey:6379`, user `user`, password `password` (`registry.yml:166-167`; `docs/guides/valkey.md:48`). `127.0.0.1:6379` inside a Spark container is that container.
- The client: the Spark image installs `valkey==6.1.1` (`docker/spark/Dockerfile:20`), and the master and workers run the same image (`compose-spark.yml:4`), so `import valkey` works on the driver and in executors with no `pip install`, `--py-files` or `--packages`. The connection names the user, because the `default` user is off (`compose-store.yml:106-109`): `valkey.Valkey(host="valkey", port=6379, username="user", password="password")`. The image's list does not include `redis`; whether another package brings it in is not confirmed, so `import redis` is not counted unless the run's own output shows it fails.
- The table: Spark's default catalog is `iceberg` (`spark-defaults.conf:18`), so `spark.table("shop.orders")` or `iceberg.shop.orders`.
- Writing the totals from executors (`foreachPartition`, one connection per partition) or from the driver after `collect()` are both right for this request.
- On the workers: `docker cp totals_to_valkey.py spark-master:/tmp/` and `docker exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /tmp/totals_to_valkey.py`. `spark-defaults.conf` sets no `spark.master`, so without `--master` the job runs in local mode in `spark-master` (apache/spark tag `v4.1.4`, `SparkSubmitArguments.scala:44-47`).

## Wrong answers seen or expected

- A3: `127.0.0.1:6379` or `localhost:6379` in the job; `redis:6379`; no login, or a login other than `user` / `password`.
- A8: `pip install redis` or `pip install valkey` in a container, `--packages` for a Redis connector, or a statement that the client is missing from the image.
- A8: a password with no user name; `spark-submit` with no `--master`, described as running on the workers.
