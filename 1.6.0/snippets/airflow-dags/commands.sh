# Commands from docs/guides/airflow-dags.md. .github/scripts/smoke.sh runs each section.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up airflow
# --8<-- [end:up]

# --8<-- [start:upload]
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
# --8<-- [end:upload]

# --8<-- [start:run]
docker exec airflow airflow dags list | grep hello
docker exec airflow airflow dags unpause hello
docker exec airflow airflow dags trigger hello
docker exec airflow airflow dags list-runs hello
# --8<-- [end:run]
