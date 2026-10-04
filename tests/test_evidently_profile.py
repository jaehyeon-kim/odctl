"""The evidently profile runs the odctl Evidently image on Postgres and SeaweedFS.

Projects, reports and dashboards go to the evidently database and dataset files
to s3://evidently/datasets. Nothing here needs Docker.
"""

from pathlib import Path

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()
REPO = Path(__file__).resolve().parents[1]


def _compose(name):
    return yaml.safe_load((RESOURCES / name).read_text())


def _evidently():
    return _compose("compose-mlops.yml")["services"]["evidently"]


def test_evidently_runs_the_odctl_image_on_host_port_8089():
    service = _evidently()
    assert service["image"] == "ghcr.io/jaehyeon-kim/odctl/evidently:${TAG:-latest}"
    assert service["profiles"] == ["evidently"]
    assert service["ports"] == ["8089:8000"]


def test_evidently_reads_its_settings_from_the_mounted_file():
    service = _evidently()
    assert service["command"] == ["--conf-path", "/etc/evidently/config.yaml"]
    assert service["volumes"] == [
        "./evidently/config.yaml:/etc/evidently/config.yaml:ro"
    ]
    env = service["environment"]
    assert env["POSTGRES_USER"] == "${POSTGRES_USER:-user}"
    assert env["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:-password}"
    # Sections from EVIDENTLY_* variables load in environment order, and
    # database ahead of storage fails at start, so none are set here.
    assert not [k for k in env if k.startswith("EVIDENTLY_")]


def test_evidently_config_keeps_state_on_postgres_and_datasets_on_s3():
    config = yaml.safe_load((RESOURCES / "evidently" / "config.yaml").read_text())
    sections = list(config)
    assert sections.index("storage") < sections.index("database")
    assert config["storage"]["type"] == "sql"
    assert config["database"]["url"].startswith("@format postgresql://")
    assert config["database"]["url"].endswith("@postgres:5432/evidently")
    assert config["dashboard"]["storage_type"] == "sql"
    assert config["dataset_storage"] == {
        "type": "fsspec",
        "path": "s3://evidently/datasets",
    }


def test_evidently_reaches_seaweedfs_and_sends_no_usage_telemetry():
    env = _evidently()["environment"]
    assert env["FSSPEC_S3_ENDPOINT_URL"] == "http://seaweed:8333"
    assert env["FSSPEC_S3_KEY"] == "${AWS_ACCESS_KEY_ID:-user}"
    assert env["FSSPEC_S3_SECRET"] == "${AWS_SECRET_ACCESS_KEY:-password}"
    assert env["DO_NOT_TRACK"] == "1"


def test_healthcheck_opens_the_database():
    test = _evidently()["healthcheck"]["test"]
    assert test[:3] == ["CMD", "python", "-c"]
    assert "http://127.0.0.1:8000/api/v2/projects" in test[3]


def test_storage_creates_the_evidently_bucket():
    init = _compose("compose-infra.yml")["services"]["seaweed-init"]
    assert " evidently'" in init["entrypoint"]


def test_postgres_creates_the_evidently_database():
    script = (RESOURCES / "postgres" / "01-init-databases.sh").read_text()
    assert 'CREATE DATABASE evidently OWNER "$POSTGRES_USER";' in script
    loop = next(line for line in script.splitlines() if line.startswith("for db in"))
    assert " evidently;" in loop


def test_the_image_adds_s3fs_and_is_built_with_the_others():
    dockerfile = (RESOURCES / "docker" / "evidently" / "Dockerfile").read_text()
    assert "FROM evidently/evidently-service:0.7.23" in dockerfile
    assert "s3fs==" in dockerfile
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "build-platform-images.yml").read_text()
    )
    for job in ("build", "merge"):
        assert "evidently" in workflow["jobs"][job]["strategy"]["matrix"]["component"]


def test_evidently_has_an_e2e_group_and_a_smoke_test():
    selector = (REPO / ".github" / "scripts" / "select-profiles.py").read_text()
    assert '    "evidently",\n' in selector
    smoke = (REPO / ".github" / "scripts" / "smoke.sh").read_text()
    assert "  evidently)  smoke_evidently ;;" in smoke
