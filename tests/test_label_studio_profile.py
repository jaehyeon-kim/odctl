"""The label-studio profile runs the official Label Studio image on Postgres.

Projects, tasks and annotations go to the labelstudio database, which the
Postgres init script creates. Nothing here needs Docker.
"""

import re
from pathlib import Path

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()
REPO = Path(__file__).resolve().parents[1]


def _services():
    return yaml.safe_load((RESOURCES / "compose-mlops.yml").read_text())["services"]


def test_label_studio_runs_the_official_image_on_host_port_8088():
    service = _services()["label-studio"]
    assert service["image"].startswith("heartexlabs/label-studio:")
    assert service["profiles"] == ["label-studio"]
    assert service["ports"] == ["127.0.0.1:8088:8080"]


def test_label_studio_keeps_its_data_in_the_labelstudio_database():
    env = _services()["label-studio"]["environment"]
    assert env["DJANGO_DB"] == "default"
    assert env["POSTGRE_HOST"] == "postgres"
    assert env["POSTGRE_NAME"] == "labelstudio"
    assert env["POSTGRE_USER"] == "${POSTGRES_USER:-user}"
    assert env["POSTGRE_PASSWORD"] == "${POSTGRES_PASSWORD:-password}"
    # Label Studio keeps no data in a volume and needs no Redis.
    assert "volumes" not in _services()["label-studio"]
    assert not [k for k in env if "REDIS" in k]


def test_odctl_starts_postgres_before_label_studio():
    registry = yaml.safe_load((RESOURCES / "registry.yml").read_text())
    assert registry["stacks"]["mlops"]["depends_on"]["label-studio"] == ["postgres"]


def test_label_studio_creates_the_documented_user_and_token():
    env = _services()["label-studio"]["environment"]
    assert env["LABEL_STUDIO_USERNAME"] == "user@odctl.io"
    assert env["LABEL_STUDIO_PASSWORD"] == "password"
    # Label Studio applies a token only when it is longer than 5 characters.
    assert len(env["LABEL_STUDIO_USER_TOKEN"]) > 5
    # Without it, the token gets 401 on a new organization.
    assert env["LABEL_STUDIO_ENABLE_LEGACY_API_TOKEN"] == "true"


def test_label_studio_sends_no_usage_analytics():
    env = _services()["label-studio"]["environment"]
    assert env["LABEL_STUDIO_COLLECT_ANALYTICS"] == "false"


def test_healthcheck_calls_the_health_route():
    test = _services()["label-studio"]["healthcheck"]["test"]
    assert "http://localhost:8080/health/" in test[1]


def test_postgres_creates_the_labelstudio_database():
    script = (RESOURCES / "postgres" / "01-init-databases.sh").read_text()
    assert 'CREATE DATABASE labelstudio OWNER "$POSTGRES_USER";' in script
    loop = next(line for line in script.splitlines() if line.startswith("for db in"))
    assert " labelstudio" in loop


def test_odctl_builds_no_label_studio_image():
    assert not (RESOURCES / "docker" / "label-studio").exists()
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "build-platform-images.yml").read_text()
    )
    for job in ("build", "merge"):
        components = workflow["jobs"][job]["strategy"]["matrix"]["component"]
        assert "label-studio" not in components


def test_label_studio_has_a_smoke_case():
    smoke = (REPO / ".github" / "scripts" / "smoke.sh").read_text()
    assert re.search(r"^  label-studio\)\s+smoke_label_studio\b", smoke, re.M)
