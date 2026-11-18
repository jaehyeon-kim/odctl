"""restart, recreate and logs reach every compose file of a plan, each run as
the project `odctl up` created."""

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

    def fake_client(compose_file=None, profiles=None):
        created.append((compose_file, profiles))
        return MagicMock()

    monkeypatch.setattr(projects, "create_client", fake_client)
    plan = {"compose-infra.yml": ["storage"], "compose-kafka.yml": ["kafka-lite"]}
    clients = projects.build_compose_clients(plan)
    assert len(clients) == 2
    assert created == [
        ("compose-infra.yml", ["storage"]),
        ("compose-kafka.yml", ["kafka-lite"]),
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


def test_recreate_starts_deps_attached_without_a_wait(monkeypatch):
    """The deps file holds a container that copies files and exits, and `compose up
    --wait` fails when a container exits, even with code 0, so `launch_stack` starts
    it attached and without `wait`; `recreate deps` now does the same."""
    clients = {}

    def fake_client(compose_file=None, profiles=None):
        clients[compose_file] = MagicMock()
        return clients[compose_file]

    monkeypatch.setattr(projects, "create_client", fake_client)
    monkeypatch.setattr(projects, "wait_for_one_shot_containers", lambda: None)

    projects.recreate_managed_containers(
        {"compose-deps.yml": ["deps"], "compose-kafka.yml": ["kafka-lite"]}, pull=True
    )

    clients["compose-deps.yml"].compose.up.assert_called_once_with(
        detach=False, force_recreate=True, pull="always"
    )
    clients["compose-kafka.yml"].compose.up.assert_called_once_with(
        detach=True, wait=True, force_recreate=True, pull="always"
    )
