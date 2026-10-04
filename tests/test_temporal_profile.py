"""The temporal profile is one container running the Temporal development server.

These checks pin what the profile relies on: gRPC and the Web UI on host ports 7233
and 8233, a listener on every interface rather than the default of localhost, the
SQLite database in the container with no volume, as for every odctl service, and metrics
on a fixed port that the telemetry profile scrapes. Nothing here needs Docker.
"""

import yaml
from typer.testing import CliRunner

from odctl.config import get_internal_resources_dir
from odctl.main import app

RESOURCES = get_internal_resources_dir()


def _compose():
    return yaml.safe_load((RESOURCES / "compose-orch.yml").read_text())


def _temporal_services():
    return {
        n: s
        for n, s in _compose()["services"].items()
        if "temporal" in (s.get("profiles") or [])
    }


def _command():
    return _temporal_services()["temporal"]["command"]


def _flag(name):
    command = _command()
    return command[command.index(name) + 1]


def test_temporal_is_one_development_server():
    services = _temporal_services()
    assert list(services) == ["temporal"]
    assert services["temporal"]["image"].startswith("temporalio/temporal:")
    assert _command()[:2] == ["server", "start-dev"]


def test_temporal_publishes_grpc_and_the_ui():
    ports = [str(p) for p in _temporal_services()["temporal"]["ports"]]
    assert ports == ["7233:7233", "8233:8233"]


def test_temporal_listens_beyond_localhost():
    # The default of localhost is unreachable through a published port.
    assert _flag("--ip") == "0.0.0.0"


def test_history_is_in_the_container_with_no_volume():
    # Like every odctl service, Temporal keeps no data across `odctl down`.
    service = _temporal_services()["temporal"]
    assert _flag("--db-filename").startswith("/home/temporal/")
    assert "volumes" not in service
    assert "volumes" not in _compose()


def test_telemetry_scrapes_the_metrics_port():
    port = _flag("--metrics-port")
    config = yaml.safe_load((RESOURCES / "prometheus" / "prometheus.yml").read_text())
    jobs = {job["job_name"]: job for job in config["scrape_configs"]}
    assert jobs["temporal"]["static_configs"][0]["targets"] == [f"temporal:{port}"]


def test_registry_starts_temporal_with_deps_only():
    registry = yaml.safe_load((RESOURCES / "registry.yml").read_text())
    orch = registry["stacks"]["orch"]
    assert "temporal" in orch["profiles"]
    assert orch["depends_on"]["temporal"] == ["deps"]


def test_explain_temporal(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no workspace, so the bundled registry is read
    result = CliRunner().invoke(app, ["explain", "temporal"])
    assert result.exit_code == 0, result.stdout
    assert "temporalio/temporal" in result.stdout
    assert "127.0.0.1:7233" in result.stdout
