"""`odctl logs` asks each compose file of a plan for its own containers."""

from unittest.mock import MagicMock

from odctl import logs


def test_get_managed_logs(monkeypatch, capsys):
    mock_client = MagicMock()
    mock_client.compose.logs.return_value = "log output"
    monkeypatch.setattr(logs, "build_compose_clients", lambda plan: [mock_client])

    logs.get_managed_logs({"dummy.yml": ["prof1"]})
    mock_client.compose.logs.assert_called_once()

    out, err = capsys.readouterr()
    assert "log output" in out


def test_logs_of_one_service_ask_only_its_file(monkeypatch):
    services = {"compose-infra.yml": ["seaweed"], "compose-kafka.yml": ["kafka"]}
    monkeypatch.setattr(
        logs, "get_stack_details", lambda f, p: (services[f], [], [], [])
    )
    asked = []

    def fake_clients(plan):
        asked.append(plan)
        return []

    monkeypatch.setattr(logs, "build_compose_clients", fake_clients)
    logs.get_managed_logs(
        {"compose-infra.yml": ["storage"], "compose-kafka.yml": ["kafka-lite"]},
        service="seaweed",
    )
    assert asked == [{"compose-infra.yml": ["storage"]}]
