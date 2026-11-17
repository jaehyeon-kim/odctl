# Reply: CI setup script for the odctl stack

I wrote `setup.sh` in this folder. It has not been run: Docker is not available on this machine, so the stack could not start. I checked the syntax with `bash -n` only.

## What the files do

**`setup.sh`** runs these steps against the stack on host ports (127.0.0.1), so it never calls Docker:

1. **Preflight.** Checks for `aws`, `curl`, `jq`, `feast` and a Python with `pyiceberg` and `pyarrow`. Checks that `feature_repo/feature_store.yaml` and the DAG file exist. Checks that the Iceberg REST catalog (8181) and Airflow (8085) respond.
2. **Iceberg table.** Creates namespace `demo` and table `demo.driver_stats` if they are missing. It then overwrites the table with three fixed rows, so repeated runs leave the same data. Columns: `driver_id`, `conv_rate`, `acc_rate`, `avg_daily_trips`, `event_timestamp`, `created`. I chose this schema myself, following the usual Feast driver-stats example. Change it if your tests expect something else.
3. **Feast.** Runs `feast apply` inside `feature_repo/`, then syncs `feature_repo/` to `s3://feast/repo`. The odctl Feast services reload when that prefix changes.
4. **Airflow.** Uploads `dags/materialize_driver_stats.py` to `s3://airflow/dags/`, waits until Airflow loads the DAG, triggers one run with a unique `run_id`, and polls until it succeeds or fails. It exits non-zero on failure or timeout.

**`reply.md`** is this file.

## Before you run it

- **`feature_repo/` has no `feature_store.yaml` and no feature definitions**, only a README. The script stops at the preflight check until you add the file. odctl's default is `.odctl/feast/feature_store.yaml`, but that file points at the container hostnames `postgres` and `valkey`. Those names do not resolve on the host, so `feast apply` must run where they do, or the file must use `127.0.0.1`.
- **`dags/materialize_driver_stats.py` only has a comment.** Airflow will not create a DAG from it, so the trigger step will time out after 180 seconds. Add the DAG definition first.
- **The DAG is paused at creation** (`DAGS_ARE_PAUSED_AT_CREATION=true`). The script does not unpause it. Check that a manual run still executes on a paused DAG in your Airflow version, and unpause it if not.
- **Concurrent CI jobs** overwrite the same table. Overlapping jobs can hit Iceberg commit conflicts. Run the jobs one at a time, or add a retry.
- **Credentials** default to odctl's `user` / `password` for S3 and Airflow. Override them with `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AIRFLOW_USER` and `AIRFLOW_PASSWORD`.

## Requirements on the CI machine

- `aws` (AWS CLI v2), `curl`, `jq`, `feast` with the extras `feast[duckdb,iceberg,redis,postgres]`, and a Python with `pyiceberg` and `pyarrow`. Set `PYTHON` if the interpreter is not `python3`. None of these are installed in `py/`, and I installed nothing.
- The stack running: `odctl up catalog storage feast airflow`.

## Tuning

`DAG_WAIT_SECONDS` (default 180) and `RUN_TIMEOUT_SECONDS` (default 1800) control the waits.

## Feast on IcebergSource

Use `warehouse=""` and `catalog_name="odctl"`, as odctl's Feast notes require. Otherwise the REST client builds the wrong URL.
