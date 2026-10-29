"""The ingestion container of the metadata profile copies custom connectors from S3.

It runs the image's own entrypoint, which installs `_METADATA_PIP_DEPS`, and then a
bash command that runs `connector_sync.py` before Airflow starts and again in the
background. These checks pin what that relies on. Nothing here needs Docker.
"""

import re

import yaml

from odctl.config import get_internal_resources_dir


def _compose(name):
    return yaml.safe_load((get_internal_resources_dir() / name).read_text())


def _ingestion():
    return _compose("compose-metadata.yml")["services"]["openmetadata-ingestion"]


def _command():
    return _ingestion()["command"][-1]


def test_ingestion_runs_the_image_entrypoint_then_a_bash_command():
    service = _ingestion()
    assert "entrypoint" not in service
    assert service["command"][:2] == ["bash", "-c"]


def test_connectors_are_copied_before_airflow_starts_and_the_loop_stays_behind():
    lines = _command().splitlines()
    once = lines.index("python /opt/odctl/connector_sync.py --once")
    loop = lines.index("python /opt/odctl/connector_sync.py &")
    start = lines.index("exec bash /opt/airflow/ingestion_dependency.sh")
    assert once < loop < start


def test_the_sync_script_is_mounted_from_the_workspace():
    mount = "./openmetadata/connector_sync.py:/opt/odctl/connector_sync.py:ro"
    assert _ingestion()["volumes"] == [mount]
    assert (
        get_internal_resources_dir() / "openmetadata" / "connector_sync.py"
    ).is_file()


def test_command_does_not_look_like_an_airflow_component_to_the_entrypoint():
    """The entrypoint waits for the Airflow database when this command names a
    component. The database settings only exist inside ingestion_dependency.sh."""
    component = r"(^|\s)(exec\s+)?airflow\s+(scheduler|dag-processor|triggerer|api-server)(\s|$)"
    assert not re.search(component, _command())


def test_connectors_folder_is_added_after_the_images_own_python_path():
    assert (
        'export PYTHONPATH="$${PYTHONPATH:+$$PYTHONPATH:}/opt/airflow/connectors"'
        in _command()
    )


def test_extra_packages_and_s3_settings_come_from_the_environment():
    env = _ingestion()["environment"]
    assert env["_PIP_ADDITIONAL_REQUIREMENTS"] == "${_METADATA_PIP_DEPS:-}"
    assert env["AWS_ACCESS_KEY_ID"] == "${AWS_ACCESS_KEY_ID:-user}"
    assert env["AWS_SECRET_ACCESS_KEY"] == "${AWS_SECRET_ACCESS_KEY:-password}"


def test_storage_creates_the_openmetadata_bucket():
    init = next(
        s
        for s in _compose("compose-infra.yml")["services"].values()
        if "BUCKETS=" in str(s.get("entrypoint", ""))
    )
    buckets = re.search(r"BUCKETS='([^']*)'", init["entrypoint"]).group(1).split()
    assert "openmetadata" in buckets


def test_metadata_starts_storage_with_it():
    registry = yaml.safe_load(
        (get_internal_resources_dir() / "registry.yml").read_text()
    )
    assert registry["stacks"]["metadata"]["depends_on"]["metadata"] == [
        "postgres",
        "storage",
    ]


def test_ingestion_is_healthy_only_once_airflow_answers_after_the_slow_start():
    check = _ingestion()["healthcheck"]
    assert "curl -fs http://localhost:8080/api/v2/monitor/health" in check["test"][-1]
    # 60 seconds of first copy, the pip install and the Airflow start.
    assert int(check["start_period"].rstrip("s")) >= 120


def test_a_one_shot_service_sets_autopilot_from_the_env_key():
    service = _compose("compose-metadata.yml")["services"]["openmetadata-init"]
    assert (
        service["environment"]["METADATA_AUTOPILOT"] == "${METADATA_AUTOPILOT:-false}"
    )
    assert service["profiles"] == ["metadata"]
    assert (
        service["depends_on"]["openmetadata-server"]["condition"] == "service_healthy"
    )
    assert service["image"] == _ingestion()["image"]
    assert "restart" not in service
    assert service["volumes"] == [
        "./openmetadata/autopilot_init.py:/opt/odctl/autopilot_init.py:ro"
    ]
    assert (
        get_internal_resources_dir() / "openmetadata" / "autopilot_init.py"
    ).is_file()


def test_ingestion_waits_for_the_one_shot_service_to_complete():
    """Without a service that depends on it, `up --wait` fails when it exits."""
    depends = _ingestion()["depends_on"]
    assert depends["openmetadata-init"]["condition"] == "service_completed_successfully"
