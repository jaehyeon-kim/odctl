"""`odctl logs` asks each compose file of a plan for its own containers."""

from unittest.mock import MagicMock

from odctl import logs
from odctl.docker import ServiceDetails, StackDetails


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
        logs,
        "get_stack_details",
        lambda f, p: StackDetails(
            [ServiceDetails(s, None, []) for s in services[f]], []
        ),
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


def _streams(fail_after):
    """A client whose stream fails after `fail_after` seconds, and one that follows
    until the test releases it."""
    import threading
    import time

    from python_on_whales.exceptions import DockerException

    release = threading.Event()

    def failing(**kwargs):
        time.sleep(fail_after)
        raise DockerException(["docker", "compose", "logs"], 1, b"", b"boom\n")
        yield  # a generator, as `compose.logs(stream=True)` is

    def following(**kwargs):
        release.wait(10)
        return iter(())

    broken, alive = MagicMock(), MagicMock()
    broken.compose.logs.side_effect = failing
    alive.compose.logs.side_effect = following
    return [("compose-alive.yml", alive), ("compose-broken.yml", broken)], release


def test_a_failed_stream_is_reported_while_another_follows():
    """The failure of one stream ended the command only once every stream ended,
    which a followed stream never does."""
    import time

    clients, release = _streams(fail_after=0)
    started = time.monotonic()
    try:
        logs._follow_all(clients, {})
    except logs.LogsError as e:
        assert e.file == "compose-broken.yml"
    else:
        raise AssertionError("no LogsError")
    finally:
        release.set()
    assert time.monotonic() - started < 3


def test_ctrl_c_after_a_failed_stream_still_reports_it():
    """Ctrl+C ended the command with exit 0 and dropped a failure already recorded."""
    import _thread
    import threading

    clients, release = _streams(fail_after=0.1)
    threading.Timer(0.3, _thread.interrupt_main).start()
    try:
        logs._follow_all(clients, {})
        raised = None
    except BaseException as e:  # a KeyboardInterrupt must not end the test run
        raised = e
    finally:
        release.set()
    assert isinstance(raised, logs.LogsError), repr(raised)
