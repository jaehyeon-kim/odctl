from unittest.mock import MagicMock
from typer.testing import CliRunner
from odctl.main import app

runner = CliRunner()


def test_down_command(monkeypatch):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["down", "--all"])
    assert result.exit_code == 0
    mock_stop.assert_called()


def test_restart_command(monkeypatch):
    mock_restart = MagicMock()
    monkeypatch.setattr("odctl.main.restart_managed_containers", mock_restart)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["restart", "kafka-lite"])
    assert result.exit_code == 0
    mock_restart.assert_called()


def test_logs_command(monkeypatch):
    mock_logs = MagicMock()
    monkeypatch.setattr("odctl.main.get_managed_logs", mock_logs)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["logs", "kafka-lite"])
    assert result.exit_code == 0
    mock_logs.assert_called()


def test_list_command(monkeypatch):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0


def test_explain_command(monkeypatch):
    result = runner.invoke(app, ["explain", "kafka-lite"])
    assert result.exit_code == 0


def test_docker_not_running(monkeypatch):
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)
    result = runner.invoke(app, ["up", "kafka-lite"])
    assert result.exit_code != 0
    assert "Docker is not reachable" in result.stdout


def test_invalid_profile(monkeypatch):
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    result = runner.invoke(app, ["up", "invalid_profile"])
    assert result.exit_code != 0
    assert "Unknown profile" in result.stdout
