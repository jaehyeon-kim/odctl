# Reply

I wrote `setup.sh` and this `reply.md`. I could not run `setup.sh` here because there is no Docker. I only checked its syntax with `bash -n`, and `odctl up airflow feast trino --dry-run` printed the expected plan.

## What `setup.sh` does
1. Takes a lock, so concurrent CI jobs on the same stack run one at a time. It uses `flock` where available and a `mkdir` lock otherwise.
2. Runs `odctl up airflow feast trino`. Profiles that are already running are left alone. The script never runs `odctl down`.
3. Uses Trino to create schema `iceberg.demo` and table `demo.driver_stats` if they don't exist. It adds three rows with `MERGE`, so repeat runs don't duplicate them.
4. Runs `feast apply` in `feature_repo/` and syncs that folder to `s3://feast/repo`, where the Feast services pick it up.
5. Uploads `dags/materialize_driver_stats.py` to `s3://airflow/dags` and waits for Airflow to register it (it re-reads every 15 s). It unpauses the DAG, since DAGs are created paused, and triggers one run with a unique run id. It waits for the run to succeed and exits non-zero if it fails or times out (`DAG_TIMEOUT`, default 600 s).

## Before you run it
- **The repo is incomplete.** `feature_repo/` holds only a README, and the DAG file is a one-line comment. There is no `feature_store.yaml` or feature definitions, so `feast apply` will fail until you add them. I wasn't asked to write them.
- **The table schema is my guess.** I used `driver_id`, `event_timestamp`, `conv_rate`, `acc_rate` and `avg_daily_trips`, from the usual Feast driver example. Change the DDL and rows to match your feature view.
- **The Iceberg source needs specific settings.** In `feature_store.yaml`, use `warehouse=""` and `catalog_name="odctl"` on the Iceberg source, as odctl's Feast notes say.
- **The CI host needs these tools:** Docker, `aws` CLI, and `feast[duckdb,iceberg,redis,postgres]`. The script talks to Trino and Airflow through `docker exec` into the `trino` and `airflow` containers.
- **Overrides:** it reads the S3 endpoint from `S3_ENDPOINT` (default `127.0.0.1:8333`) and the S3 credentials from `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (default `user`/`password`). It also honours `ODCTL`, `SETUP_LOCK` and `DAG_TIMEOUT`.
- **The lock only works on a shared filesystem.** It does not coordinate jobs that run on different hosts.
- **Each CI job adds one DAG run to Airflow's history.**
- **I haven't tested the Airflow commands.** `dags state` and `dags trigger --run-id` are the Airflow 3 CLI as I remember it. Check them against your stack on the first run.
