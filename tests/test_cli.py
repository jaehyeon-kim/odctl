from unittest.mock import MagicMock

from typer.testing import CliRunner

from dml.main import app

runner = CliRunner()


def test_info_command(monkeypatch):
    """Validates the package metadata command."""
    monkeypatch.setattr("dml.workspace.get_cli_version", lambda: "0.0.3")
    monkeypatch.setattr("dml.docker.is_docker_running", lambda: True)

    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Open DataML Stack" in result.stdout
    assert "0.0.3" in result.stdout
    assert "Reachable" in result.stdout


def test_up_command_dry_run(monkeypatch, mock_registry_data):
    """Validates that a dry run safely loops through without calling Docker client commands."""
    monkeypatch.setattr("dml.planner.load_registry", lambda: mock_registry_data)
    mock_launch = MagicMock()
    monkeypatch.setattr("dml.docker.launch_stack", mock_launch)

    result = runner.invoke(app, ["up", "kafka", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry Run" in result.stdout
    mock_launch.assert_not_called()


def test_up_command_execution(monkeypatch, mock_registry_data):
    """Validates standard up command triggers the underlying Docker pipeline components."""
    # Mock the planner registry resolver so it uses our test data
    monkeypatch.setattr("dml.planner.load_registry", lambda: mock_registry_data)

    # Force the CLI's Docker health check to return True
    monkeypatch.setattr("dml.main.is_docker_running", lambda: True)

    # Create a single spy mock for the launch function
    mock_launch = MagicMock()
    monkeypatch.setattr("dml.main.launch_stack", mock_launch)

    # Execute the CLI command
    result = runner.invoke(app, ["up", "kafka"])

    # Verify successful completion and that launch_stack was hit with the right args
    assert result.exit_code == 0
    mock_launch.assert_called_once_with("compose-infra.yml", ["kafka"])
