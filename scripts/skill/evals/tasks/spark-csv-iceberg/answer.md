# spark-csv-iceberg

Answer sheet of the case `spark-csv-iceberg`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A8 (stack setting or image content assumed), A1 (a step needs an earlier step), A10 (a check that cannot fail).

## Records

- planning `architecting-analytics/review-labs.md:39` and `:44`: `seaweedfs:8333`, `storage:8333` and `admin/admin`, which do not exist (A3).
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): the container address `catalog:8181` used from the host (A3).
- planning `architecting-analytics/validation-live-stack.md:146`: the Spark image assumed to hold `hadoop-aws`; since then odctl puts it in the shared volume, so the case checks the opposite assumption, a `--packages` or extra S3 settings for what `spark-defaults.conf` already sets (A8).
- planning `odctl/release/1.4.0/reader-check.md:10`: a step that needs a table from an earlier step (A1).
- planning `architecting-analytics/validation-live-stack.md:153`: a check made against a document, not the table (A10).

## Right answer

- `odctl up spark-full` (already running; `spark-full` brings `catalog`, `postgres` and `storage`, `registry.yml:122-123`, `58`).
- A bucket that exists: `seaweed-init` creates `warehouse`, `odctl-dev`, `flink-checkpoints` and others at each start (`compose-infra.yml:109-113`). `odctl-dev` or `warehouse` is right; a new bucket must be created first (`docs/how-it-works.md:250-263`).
- Upload from the host: S3 API `http://127.0.0.1:8333`, keys `user` and `password` (`registry.yml:47-50`), region `us-east-1` and path-style access (`docs/snippets/feast-iceberg/commands.sh:17-24`). Requests must be signed: the S3 API refuses anonymous requests with 403 (`smoke.sh:552-554`). Any S3 client works, for example `curl --aws-sigv4 aws:amz:us-east-1:s3 --user user:password -T trips.csv http://127.0.0.1:8333/odctl-dev/trips.csv` (`smoke.sh:555-560`), the AWS CLI or boto3.
- The job reads `s3a://odctl-dev/trips.csv` (or `s3://`) with `header` set: `spark-defaults.conf:34-42` maps both schemes to S3A with endpoint `http://seaweed:8333` and the keys, and `hadoop-aws` with the AWS SDK bundle is in the shared volume (`deps/fetch_spark_dependencies.sh:70-71`) on the classpath (`spark-defaults.conf:5-6`). No `--packages` and no S3 settings in the job. Not confirmed by a run: no smoke check reads a plain file through S3A; the Iceberg checks use S3FileIO.
- `CREATE NAMESPACE IF NOT EXISTS iceberg.taxi` (or `taxi`) before the table is written (`docs/snippets/spark/commands.sh:15`); the default catalog is `iceberg` (`spark-defaults.conf:18`), so `taxi.trips` names the Iceberg table.
- The job runs in `spark-master`: `docker cp load_trips.py spark-master:/tmp/` and `docker exec spark-master /opt/spark/bin/spark-submit /tmp/load_trips.py` (`docs/snippets/spark/commands.sh:34-35`), with or without `--master spark://spark-master:7077`.
- The check, from the host, reads the table through the REST catalog at `http://127.0.0.1:8181` (`registry.yml:62`): `GET /v1/namespaces/taxi/tables/trips` and the current snapshot's `total-records` (`docs/snippets/iceberg-ingestion/commands.sh:34`), or PyIceberg with the host addresses. It compares that number with the number of data lines in `trips.csv` (6, the header excluded) and exits 1 when they differ or when the table or snapshot is missing. When the job appends and the file is loaded twice, `total-records` doubles; the check then fails, which is right.

## Wrong answers seen or expected

- A3: `http://seaweed:8333` or `http://catalog:8181` in a command run on the laptop; `http://127.0.0.1:8333` or `localhost:8333` inside the Spark job; `seaweedfs`, `storage` or `minio` as a host name; `admin/admin` or `minioadmin`.
- A8: `--packages org.apache.hadoop:hadoop-aws...`, or `fs.s3a.*` and catalog settings repeated in the job and described as required.
- A1: writing the table with no `CREATE NAMESPACE` first; uploading to a bucket no step creates.
- A10: a check that passes when the table exists or has any rows, without comparing with the file's 6 trips; a check that reads a local file or the job's output instead of the table.
