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

    services, ports, images, volumes = docker.get_stack_details(
        "compose-test.yml", ["prof1"]
    )
    assert services == ["test-service"]
    assert ports == ["test-service:8080:80"]
    assert images == ["test-service -> test-image:latest"]
    assert volumes == ["my-vol"]


def test_get_stack_details_missing_file(monkeypatch):
    monkeypatch.setattr(docker, "get_compose_path", lambda x: Path("/nonexistent/file"))
    services, ports, images, volumes = docker.get_stack_details(
        "compose-test.yml", ["prof1"]
    )
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
    # remove_orphans is what clears containers whose service was dropped
    # from the compose file.
    mock_client.compose.down.assert_called_with(volumes=True, remove_orphans=True)


def test_restart_managed_containers(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(docker, "_build_compose_client", lambda plan: mock_client)
    docker.restart_managed_containers({"dummy.yml": ["prof1"]})
    mock_client.compose.restart.assert_called_once()


def test_get_managed_containers(monkeypatch):
    # Mock get_stack_details
    monkeypatch.setattr(
        docker, "get_stack_details", lambda f, p: (["test-service"], [], [], [])
    )

    mock_container = MagicMock()
    mock_container.config.labels = {
        "com.docker.compose.project": "odctl-test",
        "com.docker.compose.service": "test-service",
    }
    mock_ignored = MagicMock()
    mock_ignored.config.labels = {
        "com.docker.compose.project": "other-test",
        "com.docker.compose.service": "test-service",
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


# ==========================================
# Preflight: images built by this project
# ==========================================

DEPS_IMAGE = "ghcr.io/jaehyeon-kim/odctl/deps"


class FakeDockerException(Exception):
    """A stand-in for python_on_whales' exception, which carries stderr."""

    def __init__(self, stderr: str):
        super().__init__("The command executed was `docker manifest inspect`.")
        self.stderr = stderr


def _preflight_plan(tmp_path, monkeypatch) -> dict:
    """Write a compose file holding one built image and one third-party image."""
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  init-deps:
    image: ghcr.io/jaehyeon-kim/odctl/deps:${TAG:-latest}
    profiles: ["prof1"]
  postgres:
    image: postgres:17.2
    profiles: ["prof1"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    return {"compose-test.yml": ["prof1"]}


def test_resolve_image_tag_reads_the_workspace_env_file(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("# Auto-generated\nTAG=1.2.3\nTZ=UTC\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("TAG", raising=False)

    assert docker.resolve_image_tag() == "1.2.3"


def test_resolve_image_tag_lets_the_shell_win(tmp_path, monkeypatch):
    """Compose gives the shell environment precedence over the .env file."""
    (tmp_path / ".env").write_text("TAG=1.2.3\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.setenv("TAG", "4.5.6")

    assert docker.resolve_image_tag() == "4.5.6"


def test_resolve_image_tag_falls_back_to_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("TAG", raising=False)

    assert docker.resolve_image_tag() == "latest"


def test_get_versioned_images_expands_the_tag_and_skips_third_party(
    tmp_path, monkeypatch
):
    plan = _preflight_plan(tmp_path, monkeypatch)
    monkeypatch.setenv("TAG", "9.9.9")

    assert docker.get_versioned_images(plan) == [f"{DEPS_IMAGE}:9.9.9"]


def test_get_versioned_images_is_empty_without_built_images(tmp_path, monkeypatch):
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  postgres:
    image: postgres:17.2
    profiles: ["prof1"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    assert docker.get_versioned_images({"compose-test.yml": ["prof1"]}) == []


def _mock_preflight_client(monkeypatch, local: bool) -> MagicMock:
    """Point the preflight at one built image and a fake Docker client."""
    mock_client = MagicMock()
    mock_client.image.exists.return_value = local
    monkeypatch.setattr(docker, "client", mock_client)
    monkeypatch.setattr(
        docker, "get_versioned_images", lambda plan: [f"{DEPS_IMAGE}:9.9.9"]
    )
    return mock_client


def test_find_unpublished_images_accepts_an_image_already_on_the_host(monkeypatch):
    """An offline machine must still start a stack whose images it has pulled."""
    mock_client = _mock_preflight_client(monkeypatch, local=True)

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []
    mock_client.manifest.inspect.assert_not_called()


def test_find_unpublished_images_accepts_a_published_image(monkeypatch):
    mock_client = _mock_preflight_client(monkeypatch, local=False)

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []
    mock_client.manifest.inspect.assert_called_once_with(f"{DEPS_IMAGE}:9.9.9")


def test_find_unpublished_images_reports_an_absent_tag(monkeypatch):
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException("manifest unknown\n")

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == [
        f"{DEPS_IMAGE}:9.9.9"
    ]


def test_find_unpublished_images_passes_an_unreachable_registry(monkeypatch):
    """No network is not evidence that a tag is absent, so the launch goes on."""
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException(
        'Get "https://ghcr.io/v2/": dial tcp: lookup ghcr.io: no such host\n'
    )

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []


def test_find_unpublished_images_survives_a_broken_local_lookup(monkeypatch):
    """A daemon error on the local lookup must not hide the registry answer."""
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.image.exists.side_effect = Exception("cannot connect to the daemon")
    mock_client.manifest.inspect.side_effect = FakeDockerException("manifest unknown\n")

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == [
        f"{DEPS_IMAGE}:9.9.9"
    ]
