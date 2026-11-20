I wrote `setup.sh`, the setup script for the test suite. It has not been run against a stack yet: Docker isn't available on this machine. I checked that both the bash and the embedded Python parse, and confirmed the script stops with a clear error when Docker can't be reached. Please do one run against the real stack before CI depends on it.

## What `setup.sh` does

It does all its work inside odctl's `airflow` container. That image already has `pyiceberg`, `boto3` and `feast[duckdb,iceberg,postgres,redis]==0.68.0`, the same Feast version as the stack's Feast services. It is also on the `odctl` network, so it can reach `catalog`, `postgres`, `seaweed` and `valkey`. The CI host only needs `docker`, `odctl`, `tar` and `python3`.

1. **Checks that the stack is up** with `odctl ps --all --json`. These containers must be running and healthy: `postgres`, `seaweed`, `iceberg-catalog`, `valkey`, `feast-serve` and `airflow`. It deliberately does **not** run `odctl up`. On a shared, long-lived stack, a checkout with a different `.odctl/` (`.env` or compose files) would recreate containers, and other jobs would lose their data.
2. **Iceberg:** creates the namespace `demo` and the table `demo.driver_stats` if they're missing. It then overwrites the table with 10 rows: drivers 1001–1005, each at now−2h and now−1h, rounded to the hour. Overwriting writes a single snapshot, so the table holds exactly these rows no matter how many jobs ran before. If the table exists with a different schema, the script drops and recreates it.
3. **Feast:** runs `feast apply` on a copy of `feature_repo/`. Only if that succeeds does it sync the repository to `s3://feast/repo`, where `feast-serve` and `feast-ui` read it. It uploads only changed files and deletes stale ones, so a repository that hasn't changed doesn't restart Feast.
4. **Airflow:**
   - Uploads `dags/materialize_driver_stats.py` to `s3://airflow/dags/`, only if its content changed.
   - Waits until Airflow has parsed that version, and fails with the stack trace if the file doesn't import.
   - Triggers one run with the id `ci__<CI run id>__<time>` and waits for `success`. On failure it lists the task states and a link to the run's logs.

Running it again on the same stack ends in the same state. Setups from CI jobs running at the same time take turns, using a lock file inside the `airflow` container.

Settings you can change through environment variables: `ODCTL`, `ODCTL_WORKSPACE`, `AIRFLOW_CONTAINER`, `DAG_PARSE_TIMEOUT` (300 s), `DAG_RUN_TIMEOUT` (1200 s), `LOCK_TIMEOUT` (1800 s) and `CI_RUN_ID`.

## Before you run it

- **Start the stack once** with `odctl up catalog feast airflow`. The script never starts, recreates or stops containers.
- **`feature_repo/` and the DAG are placeholders right now.** `feature_repo/` holds only a README, and the DAG file has only a comment. The script will fail at `feast apply` and at the DAG import until the real files are there. If `feature_repo/` has no `feature_store.yaml`, the script uses odctl's (`.odctl/feast/feature_store.yaml`).
- **The table schema is my assumption**, based on Feast's usual driver example: `driver_id` long, `event_timestamp` timestamptz, `conv_rate` double, `acc_rate` double, `avg_daily_trips` long, `created` timestamptz. Change `setup_iceberg()` if your feature view expects different columns. The rows' timestamps follow the clock so that materialization and the feature view's TTL always find them.
- **The `IcebergSource` needs `warehouse=""` and `catalog_name="odctl"`.** That is how odctl's Feast and Airflow containers set up the Iceberg catalog.
- **Pausing:** new DAGs start paused on this stack. The script unpauses the DAG for its run and then pauses it again. If the DAG has a schedule, use `schedule=None` (or `catchup=False`) anyway, so the scheduler doesn't start extra runs during that window.
- **Shared stack:** the lock covers only the setups themselves. Each setup replaces the table's rows, the Feast definitions and the online features. A job whose tests are still running while another job runs its setup can therefore see that other job's data. If that matters, run the jobs one at a time, for example with one concurrency group per stack.
- The script creates no other files; it only adds `demo.driver_stats`, `s3://feast/repo` and `s3://airflow/dags/` on the stack.
