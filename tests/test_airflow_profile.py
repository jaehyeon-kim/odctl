"""The airflow profile is one container running `airflow standalone`.

It replaced separate api-server, scheduler, triggerer, dag-processor, init and
aws-cli sync containers in 0.8.0. These checks pin what the single container relies
on: one service on host port 8085, DAGs read from s3://airflow through the S3 DAG
bundle, tasks calling the Execution API in the same container, and the fixed login.
Nothing here needs Docker.
"""

import json

import yaml

from odctl.config import get_internal_resources_dir


def _airflow_services():
    compose = yaml.safe_load(
        (get_internal_resources_dir() / "compose-orch.yml").read_text()
    )
    return {
        n: s
        for n, s in compose["services"].items()
        if "airflow" in (s.get("profiles") or [])
    }


def _env():
    return _airflow_services()["airflow"]["environment"]


def test_airflow_is_one_standalone_service():
    services = _airflow_services()
    assert list(services) == ["airflow"]
    assert "exec airflow standalone" in services["airflow"]["command"][-1]


def test_airflow_publishes_8085():
    assert [str(p) for p in _airflow_services()["airflow"]["ports"]] == ["8085:8080"]


def test_dags_come_from_the_s3_bundle():
    bundles = json.loads(_env()["AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST"])
    assert [b["classpath"] for b in bundles] == [
        "airflow.providers.amazon.aws.bundles.s3.S3DagBundle"
    ]
    assert bundles[0]["kwargs"]["bucket_name"] == "airflow"
    assert bundles[0]["kwargs"]["prefix"] == "dags"
    connection = json.loads(_env()["AIRFLOW_CONN_AWS_DEFAULT"])
    assert connection["extra"]["endpoint_url"] == "http://seaweed:8333"


def test_tasks_reach_the_execution_api_in_the_same_container():
    assert _env()["AIRFLOW__CORE__EXECUTION_API_SERVER_URL"].startswith(
        "http://localhost:8080/"
    )


def test_login_is_fixed_for_simple_auth_manager():
    env = _env()
    assert env["AIRFLOW__CORE__AUTH_MANAGER"].endswith("SimpleAuthManager")
    assert env["AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS"] == "user:admin"
    assert '{"user": "password"}' in _airflow_services()["airflow"]["command"][-1]
