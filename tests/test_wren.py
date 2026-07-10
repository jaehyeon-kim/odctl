import json
from unittest.mock import MagicMock

from typer.testing import CliRunner

from odctl.main import app

runner = CliRunner()


def test_wren_auto_setup_ch_lite(monkeypatch):
    """Test that auto-setup generates the correct ClickHouse connection payload."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    mock_call = MagicMock(return_value=0)
    monkeypatch.setattr("subprocess.call", mock_call)

    # We also mock sys.exit because main.py calls sys.exit(exit_code)
    # Using side_effect=SystemExit ensures the function actually terminates
    mock_exit = MagicMock(side_effect=SystemExit)
    monkeypatch.setattr("sys.exit", mock_exit)

    captured_payload = {}
    original_dump = json.dump

    def mock_json_dump(obj, fp, *args, **kwargs):
        captured_payload.update(obj)
        original_dump(obj, fp, *args, **kwargs)

    monkeypatch.setattr("json.dump", mock_json_dump)

    try:
        runner.invoke(app, ["wren", "auto-setup", "ch-lite"])
    except SystemExit:
        pass

    assert captured_payload["type"] == "clickhouse"
    assert captured_payload["properties"]["host"] == "clickhouse-11"
    assert captured_payload["properties"]["port"] == 8123
    assert captured_payload["properties"]["user"] == "default"

    assert mock_run.call_count == 1
    cp_args = mock_run.call_args[0][0]
    assert cp_args[0] == "docker"
    assert cp_args[1] == "cp"
    assert cp_args[3] == "wren-ai-service:/tmp/conn.json"

    assert mock_call.call_count == 1
    exec_args = mock_call.call_args[0][0]
    assert exec_args == [
        "docker",
        "exec",
        "-it",
        "wren-ai-service",
        "wren",
        "profile",
        "add",
        "ch-lite",
        "--from-file",
        "/tmp/conn.json",
    ]

    mock_exit.assert_called_once_with(0)


def test_wren_auto_setup_trino(monkeypatch):
    """Test that auto-setup generates the correct Trino connection payload."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    mock_call = MagicMock(return_value=0)
    monkeypatch.setattr("subprocess.call", mock_call)

    mock_exit = MagicMock(side_effect=SystemExit)
    monkeypatch.setattr("sys.exit", mock_exit)

    captured_payload = {}
    original_dump = json.dump

    def mock_json_dump(obj, fp, *args, **kwargs):
        captured_payload.update(obj)
        original_dump(obj, fp, *args, **kwargs)

    monkeypatch.setattr("json.dump", mock_json_dump)

    try:
        runner.invoke(app, ["wren", "auto-setup", "trino"])
    except SystemExit:
        pass

    assert captured_payload["type"] == "trino"
    assert captured_payload["properties"]["host"] == "trino"
    assert captured_payload["properties"]["port"] == 8080
    assert captured_payload["properties"]["user"] == "admin"


def test_wren_auto_setup_unsupported(monkeypatch):
    """Test that unsupported profiles exit safely."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    # Note: Typer catches SystemExit when using raise typer.Exit(1) via the runner.
    result = runner.invoke(app, ["wren", "auto-setup", "invalid-profile"])

    # Typer Exit(1) translates to exit_code 1
    assert result.exit_code == 1
    assert "Auto-setup does not support profile: invalid-profile" in result.stdout
