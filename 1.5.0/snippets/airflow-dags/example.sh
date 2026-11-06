#!/usr/bin/env bash
# Starts airflow, uploads a DAG to s3://airflow/dags, waits until Airflow has
# parsed it, triggers a run and waits until the run finishes.
set -euo pipefail

odctl up airflow

docker exec -i airflow python - <<'PY'
import boto3
body = '''
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
import pendulum

with DAG(
    dag_id="hello",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
):
    BashOperator(task_id="say_hello", bash_command="echo hello")
'''
boto3.client("s3", endpoint_url="http://seaweed:8333").put_object(
    Bucket="airflow", Key="dags/hello.py", Body=body.encode())
PY

# Airflow checks the bucket every 15 seconds, then parses the new file.
until docker exec airflow airflow dags list 2>/dev/null | grep hello >/dev/null; do sleep 5; done
docker exec airflow airflow dags unpause hello
docker exec airflow airflow dags trigger hello >/dev/null

until docker exec airflow airflow dags list-runs hello -o plain 2>/dev/null | grep -E 'success|failed' >/dev/null; do sleep 5; done
docker exec airflow airflow dags list-runs hello -o plain
