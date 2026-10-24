"""restart, recreate and logs reach every compose file of a plan, each run as
the project `odctl up` created."""

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from odctl import projects
from odctl.config import INTERNAL_RESOURCES_DIR


def test_restart_managed_containers(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(projects, "build_compose_clients", lambda plan: [mock_client])
    projects.restart_managed_containers({"dummy.yml": ["prof1"]})
    mock_client.compose.restart.assert_called_once()


def test_compose_clients_run_each_file_as_its_own_project(monkeypatch):
    """`up` runs each compose file as its own project, named by the file. One
    client over several files merged them into one project, so `recreate` met
    "Conflict. The container name "/seaweed" is already in use", and `restart`
    and `logs` left out the containers of the other files."""
    created = []

    def fake_client(compose_files=None, profiles=None):
        created.append((compose_files, profiles))
        return MagicMock()

    monkeypatch.setattr(projects, "create_client", fake_client)
    monkeypatch.setattr(projects, "get_compose_path", lambda f: Path("/ws") / f)
    plan = {"compose-infra.yml": ["storage"], "compose-kafka.yml": ["kafka-lite"]}
    clients = projects.build_compose_clients(plan)
    assert len(clients) == 2
    assert created == [
        ([str(Path("/ws/compose-infra.yml"))], ["storage"]),
        ([str(Path("/ws/compose-kafka.yml"))], ["kafka-lite"]),
    ]


def test_every_compose_file_names_its_project():
    """The per-file clients rely on each file's top-level `name:`, the project
    `up` creates its containers under."""
    for path in sorted(INTERNAL_RESOURCES_DIR.glob("compose-*.yml")):
        name = yaml.safe_load(path.read_text()).get("name")
        assert name == f"odctl-{path.stem.removeprefix('compose-')}", path.name


def test_recreate_and_restart_act_on_every_file_of_the_plan(monkeypatch):
    infra, kafka = MagicMock(), MagicMock()
    monkeypatch.setattr(projects, "build_compose_clients", lambda plan: [infra, kafka])
    monkeypatch.setattr(projects, "wait_for_one_shot_containers", lambda: None)
    plan = {"compose-infra.yml": ["storage"], "compose-kafka.yml": ["kafka-lite"]}
    projects.recreate_managed_containers(plan)
    projects.restart_managed_containers(plan)
    for client in (infra, kafka):
        client.compose.up.assert_called_once()
        client.compose.restart.assert_called_once()


def test_recreate_waits_for_one_shot_containers_before_and_after(monkeypatch):
    calls = []
    mock_client = MagicMock()
    mock_client.compose.up.side_effect = lambda **kw: calls.append("up")
    monkeypatch.setattr(projects, "build_compose_clients", lambda plan: [mock_client])
    monkeypatch.setattr(
        projects, "wait_for_one_shot_containers", lambda: calls.append("wait")
    )
    projects.recreate_managed_containers({"compose-infra.yml": ["storage"]})
    assert calls == ["wait", "up", "wait"]
