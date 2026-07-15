import pytest
from pathlib import Path
from unittest.mock import MagicMock
from odctl import docker

def test_is_docker_running_success(monkeypatch):
    mock_client = MagicMock()
    mock_client.system.info.return_value = {}
    monkeypatch.setattr(docker, "client", mock_client)
    assert docker.is_docker_running() is True

def test_is_docker_running_fail(monkeypatch):
    mock_client = MagicMock()
    mock_client.system.info.side_effect = Exception("error")
    monkeypatch.setattr(docker, "client", mock_client)
    assert docker.is_docker_running() is False

def test_get_stack_details(tmp_path, monkeypatch):
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  test-service:
    image: test-image:latest
    profiles: ["prof1"]
    ports:
      - "8080:80"
    volumes:
      - my-vol:/data
  test-service-2:
    profiles: ["prof2"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    
    services, ports, images, volumes = docker.get_stack_details("compose-test.yml", ["prof1"])
    assert services == ["test-service"]
    assert ports == ["test-service:8080:80"]
    assert images == ["test-service -> test-image:latest"]
    assert volumes == ["my-vol"]

def test_get_stack_details_missing_file(monkeypatch):
    monkeypatch.setattr(docker, "get_compose_path", lambda x: Path("/nonexistent/file"))
    services, ports, images, volumes = docker.get_stack_details("compose-test.yml", ["prof1"])
    assert "File Error" in services[0]

def test_docker_actions(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(docker, "_create_client", lambda **kw: mock_client)
    monkeypatch.setattr(docker, "get_compose_path", lambda x: "dummy.yml")
    
    docker.pull_stack_images("dummy.yml", ["prof1"])
    mock_client.compose.pull.assert_called_once()
    
    docker.launch_stack("dummy.yml", ["prof1"])
    mock_client.compose.up.assert_called_with(detach=True, wait=True)
    
    docker.launch_stack("dummy.yml", ["deps"])
    mock_client.compose.up.assert_called_with(detach=False)
    
    docker.stop_stack("dummy.yml", ["prof1"], remove_volumes=True)
    mock_client.compose.down.assert_called_with(volumes=True)

def test_restart_managed_containers(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(docker, "_build_compose_client", lambda plan: mock_client)
    docker.restart_managed_containers({"dummy.yml": ["prof1"]})
    mock_client.compose.restart.assert_called_once()

def test_get_managed_containers(monkeypatch):
    # Mock get_stack_details
    monkeypatch.setattr(docker, "get_stack_details", lambda f, p: (["test-service"], [], [], []))
    
    mock_container = MagicMock()
    mock_container.config.labels = {
        "com.docker.compose.project": "odctl-test",
        "com.docker.compose.service": "test-service"
    }
    mock_ignored = MagicMock()
    mock_ignored.config.labels = {
        "com.docker.compose.project": "other-test",
        "com.docker.compose.service": "test-service"
    }
    mock_client = MagicMock()
    mock_client.container.list.return_value = [mock_container, mock_ignored]
    monkeypatch.setattr(docker, "client", mock_client)
    
    res = docker.get_managed_containers({"dummy.yml": ["prof1"]})
    assert len(res) == 1
    assert res[0] == mock_container

def test_get_managed_logs(monkeypatch, capsys):
    mock_client = MagicMock()
    mock_client.compose.logs.return_value = "log output"
    monkeypatch.setattr(docker, "_build_compose_client", lambda plan: mock_client)
    
    docker.get_managed_logs({"dummy.yml": ["prof1"]})
    mock_client.compose.logs.assert_called_once()
    
    out, err = capsys.readouterr()
    assert "log output" in out

