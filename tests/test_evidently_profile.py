"""The evidently profile runs the official Evidently image on Postgres.

Projects, reports, dashboards and datasets go to the evidently database. Nothing
here needs Docker.
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


def test_evidently_runs_the_official_image_on_host_port_8089():
    service = _evidently()
    assert service["image"].startswith("evidently/evidently-service:")
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


def test_evidently_config_keeps_everything_on_postgres():
    config = yaml.safe_load((RESOURCES / "evidently" / "config.yaml").read_text())
    sections = list(config)
    assert sections.index("storage") < sections.index("database")
    assert config["storage"]["type"] == "sql"
    assert config["database"]["url"].startswith("@format postgresql://")
    assert config["database"]["url"].endswith("@postgres:5432/evidently")
    assert config["dashboard"]["storage_type"] == "sql"
    # Without dataset_storage, datasets go to the database with the rest.
    assert "dataset_storage" not in config


def test_evidently_sends_no_usage_telemetry():
    assert _evidently()["environment"]["DO_NOT_TRACK"] == "1"


def test_healthcheck_opens_the_database():
    test = _evidently()["healthcheck"]["test"]
    assert test[:3] == ["CMD", "python", "-c"]
    assert "http://127.0.0.1:8000/api/v2/projects" in test[3]


def test_postgres_creates_the_evidently_database():
    script = (RESOURCES / "postgres" / "01-init-databases.sh").read_text()
    assert 'CREATE DATABASE evidently OWNER "$POSTGRES_USER";' in script
    loop = next(line for line in script.splitlines() if line.startswith("for db in"))
    assert " evidently;" in loop


def test_odctl_builds_no_evidently_image():
    assert not (RESOURCES / "docker" / "evidently").exists()
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "build-platform-images.yml").read_text()
    )
    for job in ("build", "merge"):
        components = workflow["jobs"][job]["strategy"]["matrix"]["component"]
        assert "evidently" not in components


def test_evidently_has_an_e2e_group_and_a_smoke_test():
    selector = (REPO / ".github" / "scripts" / "select-profiles.py").read_text()
    assert '    "evidently",\n' in selector
    smoke = (REPO / ".github" / "scripts" / "smoke.sh").read_text()
    assert "  evidently)  smoke_evidently ;;" in smoke
