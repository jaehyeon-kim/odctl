from unittest.mock import MagicMock
from typer.testing import CliRunner
from odctl.main import app

runner = CliRunner()


def test_down_command(monkeypatch):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    # Mock get_managed_containers to return a fake container so down --all proceeds
    mock_container = MagicMock()
    mock_container.config.labels = {"com.docker.compose.service": "kafka"}
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda x: [mock_container]
    )
    monkeypatch.setattr(
        "odctl.docker.get_stack_details",
        lambda x, y: (["kafka"], [], [], []),
    )

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


def _stopped_files(mock_stop):
    """The compose files a mocked stop_stack was asked to tear down, in order."""
    return [call.args[0] for call in mock_stop.call_args_list]


def test_down_named_profile_with_volumes_also_removes_shared_deps(monkeypatch):
    """`odctl down kafka-lite -v` must not leave the deps init container, the
    odctl network and the shared JAR volume behind."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    # Nothing else is left running, so deps is safe to remove.
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [])

    result = runner.invoke(app, ["down", "kafka-lite", "-v"])

    assert result.exit_code == 0
    files = _stopped_files(mock_stop)
    assert "compose-deps.yml" in files, files
    deps_call = mock_stop.call_args_list[-1]
    assert deps_call.args[0] == "compose-deps.yml"
    assert deps_call.args[1] == ["deps"]
    assert deps_call.kwargs["remove_volumes"] is True


def test_down_named_profile_keeps_shared_deps_while_others_run(monkeypatch):
    """Another profile still holding containers needs the network and the volume,
    so deps must survive."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [MagicMock()])

    result = runner.invoke(app, ["down", "kafka-lite", "-v"])

    assert result.exit_code == 0
    assert "compose-deps.yml" not in _stopped_files(mock_stop)


def test_down_named_profile_without_volumes_keeps_shared_deps(monkeypatch):
    """Without -v the data is meant to survive, and so is the shared volume."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [])

    result = runner.invoke(app, ["down", "kafka-lite"])

    assert result.exit_code == 0
    assert "compose-deps.yml" not in _stopped_files(mock_stop)


def test_down_all_with_volumes_removes_deps_exactly_once(monkeypatch):
    """`--all` already carries deps in its plan, so the idle check must not add a
    second teardown of the same project."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.typer.confirm", lambda *a, **k: True)

    mock_container = MagicMock()
    mock_container.config.labels = {"com.docker.compose.service": "init-deps"}
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: [mock_container]
    )
    monkeypatch.setattr(
        "odctl.docker.get_stack_details",
        lambda f, p: (["init-deps"], [], [], ["odctl-shared-deps"]),
    )

    result = runner.invoke(app, ["down", "--all", "-v"])

    assert result.exit_code == 0
    assert _stopped_files(mock_stop).count("compose-deps.yml") == 1
