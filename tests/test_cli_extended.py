import sys
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock
from typer.testing import CliRunner
from odctl.docker import ServiceDetails, StackDetails, get_stack_details
from odctl.main import app
from cli_workspace import fake_container, fake_containers, write_workspace

runner = CliRunner()


def _stack(names, volumes=()):
    """A get_stack_details result with these service names and named volumes."""
    return StackDetails([ServiceDetails(n, None, []) for n in names], list(volumes))


def test_down_command(monkeypatch):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    # Mock get_managed_containers to return a fake container so down --all proceeds
    mock_container = MagicMock()
    mock_container.config.labels = {"com.docker.compose.service": "kafka"}
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda x: [mock_container])
    monkeypatch.setattr(
        "odctl.main.get_stack_details",
        lambda x, y: _stack(["kafka"]),
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


def test_recreate_command(monkeypatch):
    mock_recreate = MagicMock()
    monkeypatch.setattr("odctl.main.recreate_managed_containers", mock_recreate)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["recreate", "kafka-lite"])
    assert result.exit_code == 0
    mock_recreate.assert_called()
    assert mock_recreate.call_args.kwargs["pull"] is False


def test_recreate_command_pull(monkeypatch):
    """--pull has to reach the primitive, or a stale image survives a recreate."""
    mock_recreate = MagicMock()
    monkeypatch.setattr("odctl.main.recreate_managed_containers", mock_recreate)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["recreate", "kafka-lite", "--pull"])
    assert result.exit_code == 0
    assert mock_recreate.call_args.kwargs["pull"] is True


def test_recreate_requires_docker(monkeypatch):
    mock_recreate = MagicMock()
    monkeypatch.setattr("odctl.main.recreate_managed_containers", mock_recreate)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)

    result = runner.invoke(app, ["recreate", "kafka-lite"])
    assert result.exit_code == 1
    mock_recreate.assert_not_called()


def test_logs_command(monkeypatch):
    mock_logs = MagicMock()
    monkeypatch.setattr("odctl.main.get_managed_logs", mock_logs)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    result = runner.invoke(app, ["logs", "kafka-lite"])
    assert result.exit_code == 0
    mock_logs.assert_called()


def _compose_failure(command="compose"):
    """A Docker error as python-on-whales raises it, with stderr captured."""
    from python_on_whales.exceptions import DockerException

    return DockerException(["docker", command], 1, b"", b"boom\n")


def test_a_failed_pull_in_up_is_reported(monkeypatch):
    """`up --pull` ran the pull outside the handler that guards the launch, so a
    failed pull ended in a traceback, while `pull` reports the same failure."""
    from odctl.planner import build_execution_plan

    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.find_unpublished_images", lambda plan: [])
    launch = MagicMock()
    monkeypatch.setattr("odctl.main.launch_stack", launch)

    def fail(file, profiles):
        raise _compose_failure("pull")

    monkeypatch.setattr("odctl.main.pull_stack_images", fail)
    first = next(iter(build_execution_plan(["kafka-lite"])))

    result = runner.invoke(app, ["up", "kafka-lite", "--pull"], env={"COLUMNS": "200"})

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert f"Failed to pull images for {first}" in result.stdout
    launch.assert_not_called()


def _clients_by_file(monkeypatch, failing_file):
    """Give each compose file its own fake client; the one of `failing_file` fails."""
    from odctl.planner import build_execution_plan, expand_plan_dependencies

    plan = expand_plan_dependencies(
        build_execution_plan(["kafka-lite"], resolve_deps=False)
    )
    clients = {file: MagicMock() for file in plan}
    error = _compose_failure()
    for name in ("restart", "up", "logs"):
        getattr(clients[failing_file].compose, name).side_effect = error
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.projects.wait_for_one_shot_containers", lambda: None)
    monkeypatch.setattr(
        "odctl.projects.build_compose_clients",
        lambda plan: [clients[file] for file in plan],
    )
    monkeypatch.setattr(
        "odctl.logs.build_compose_clients",
        lambda plan: [clients[file] for file in plan],
    )
    return plan


@pytest.mark.parametrize(
    "command, verb, done",
    [
        (["restart", "kafka-lite"], "restart", "Restarting"),
        (["recreate", "kafka-lite"], "recreate", "Recreating"),
        (["logs", "kafka-lite"], "fetch logs for", None),
    ],
    ids=["restart", "recreate", "logs"],
)
def test_a_compose_failure_names_its_file(monkeypatch, command, verb, done):
    """restart, recreate and logs ended in a traceback on a failed Compose call, and
    nothing said which files recreate had already replaced."""
    plan = _clients_by_file(monkeypatch, "compose-kafka.yml")

    result = runner.invoke(app, command, env={"COLUMNS": "200"})

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert f"Failed to {verb} compose-kafka.yml" in result.stdout
    assert "boom" in result.stdout
    if done:
        for file in plan:
            assert f"{done} {file}" in result.stdout
            if file == "compose-kafka.yml":
                break


def test_a_failed_log_stream_exits_1(monkeypatch):
    """A follow stream fails in its own thread, which printed a thread traceback
    and left the command to exit 0."""
    _clients_by_file(monkeypatch, "compose-kafka.yml")

    result = runner.invoke(
        app,
        ["logs", "kafka-lite", "-f", "--since", "10minutes"],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 1
    assert "Failed to fetch logs for compose-kafka.yml" in result.stdout


def test_logs_of_a_service_no_file_defines_is_an_error(monkeypatch):
    """Compose refuses a service its file does not define; odctl printed nothing
    and exited 0."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    built = MagicMock(return_value=[])
    monkeypatch.setattr("odctl.logs.build_compose_clients", built)

    result = runner.invoke(
        app, ["logs", "kafka-lite", "--service", "nosuch"], env={"COLUMNS": "200"}
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "nosuch" in result.stdout
    assert "kafka-lite" in result.stdout
    built.assert_not_called()


# The expected text is what the commands print for the fixed workspace in
# tests/cli_workspace.py at 100 columns.
LIST_OUTPUT = """\
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Profile    ┃ Parent Stack ┃ Description                    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ base       │ base         │ Shared network and setup.      │
├────────────┼──────────────┼────────────────────────────────┤
│ kafka-lite │ streaming    │ Event streaming for the tests. │
│ kafka-full │              │                                │
├────────────┼──────────────┼────────────────────────────────┤
│ valkey     │ streaming    │ An in-memory cache.            │
└────────────┴──────────────┴────────────────────────────────┘
"""

LIST_DETAILS_OUTPUT = """\
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Profile    ┃ Parent Stack ┃ Description            ┃ Services          ┃ Port Mappings           ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ base       │ base         │ Shared network and     │ init-base         │ N/A                     │
│            │              │ setup.                 │                   │                         │
├────────────┼──────────────┼────────────────────────┼───────────────────┼─────────────────────────┤
│ kafka-lite │ streaming    │ Event streaming for    │ kafka, kafka-ui   │ kafka-ui:127.0.0.1:808… │
│            │              │ the tests.             │                   │ kafka:127.0.0.1:9092:9… │
│ kafka-full │              │                        │ kafka-1, kafka-ui │ kafka-1:127.0.0.1:9093… │
│            │              │                        │                   │ kafka-ui:127.0.0.1:808… │
├────────────┼──────────────┼────────────────────────┼───────────────────┼─────────────────────────┤
│ valkey     │ streaming    │ An in-memory cache.    │ valkey            │ valkey:127.0.0.1:16379… │
│            │              │                        │                   │ valkey:127.0.0.1:6379:… │
└────────────┴──────────────┴────────────────────────┴───────────────────┴─────────────────────────┘
"""

EXPLAIN_KAFKA_LITE_OUTPUT = """\
╭──────────────────────────────── 🔍 Profile Inspector: kafka-lite ────────────────────────────────╮
│ Parent Stack: streaming                                                                          │
│ Compose File: compose-kafka.yml                                                                  │
│                                                                                                  │
│ Description:                                                                                     │
│ Event streaming for the tests.                                                                   │
│                                                                                                  │
│ Architecture Role:                                                                               │
│ A broker with a dashboard.                                                                       │
│                                                                                                  │
│ Requires Dependencies:                                                                           │
│   base                                                                                           │
│                                                                                                  │
│ Persistent Volumes:                                                                              │
│   💾 ui-data                                                                                     │
│   (Use 'odctl down -v' to wipe these volumes)                                                    │
│                                                                                                  │
│ Containers (Images):                                                                             │
│   📦 kafka                  (apache/kafka:4.3.2)                                                 │
│       ↳ Event Broker / Kafka Connect                                                             │
│   📦 kafka-ui               (ghcr.io/kafbat/kafka-ui:v1.5.0)                                     │
│       ↳ Kafka Dashboard                                                                          │
│                                                                                                  │
│ Network Mapping (Host → Docker):                                                                 │
│   🔌 Host 8086  → Container kafka-ui:8080                                                        │
│   🔌 Host 9092  → Container kafka:9092                                                           │
│                                                                                                  │
│ 🚀 How to Use It:                                                                                │
│ Dashboard: http://127.0.0.1:8086                                                                 │
│ Install with pip install feast[duckdb].                                                          │
│                                                                                                  │
│ Note:                                                                                            │
│ Host addresses use 127.0.0.1. With IPv6 enabled in Docker, localhost can reach a service's IPv6  │
│ address, and services that listen on IPv4 only reset the connection. localhost works when        │
│ Docker's IPv6 is off.                                                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
"""

EXPLAIN_VALKEY_OUTPUT = """\
╭────────────────────────────────── 🔍 Profile Inspector: valkey ──────────────────────────────────╮
│ Parent Stack: streaming                                                                          │
│ Compose File: compose-cache.yml                                                                  │
│                                                                                                  │
│ Description:                                                                                     │
│ An in-memory cache.                                                                              │
│                                                                                                  │
│ Requires Dependencies:                                                                           │
│   base, kafka-lite                                                                               │
│                                                                                                  │
│ Persistent Volumes:                                                                              │
│   None                                                                                           │
│                                                                                                  │
│ Containers (Images):                                                                             │
│   📦 valkey                 (valkey/valkey-bundle:9)                                             │
│       ↳ In-Memory Cache & Vector DB                                                              │
│                                                                                                  │
│ Network Mapping (Host → Docker):                                                                 │
│   🔌 Host 16379 → Container valkey:6380/udp                                                      │
│   🔌 Host 6379  → Container valkey:6379                                                          │
│ Note:                                                                                            │
│ Host addresses use 127.0.0.1. With IPv6 enabled in Docker, localhost can reach a service's IPv6  │
│ address, and services that listen on IPv4 only reset the connection. localhost works when        │
│ Docker's IPv6 is off.                                                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
"""

PS_ALL_OUTPUT = """\
🌟 Active Profiles: base, kafka-lite

┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Container ┃ Service   ┃ State      ┃ Health    ┃ Ports           ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ init-base │ init-base │ exited     │ -         │ -               │
│ kafka     │ kafka     │ running    │ starting  │ 9092 → 9092/tcp │
│ kafka-ui  │ kafka-ui  │ running    │ healthy   │ 8086 → 8080/tcp │
│ odd       │ -         │ restarting │ unhealthy │ -               │
└───────────┴───────────┴────────────┴───────────┴─────────────────┘
"""


def _invoke_in_fixed_workspace(monkeypatch, tmp_path, args):
    """Run a command in the fixed workspace, at the width the expected text has."""
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    return runner.invoke(app, args, env={"COLUMNS": "100"})


def test_list_command(monkeypatch, tmp_path):
    """The tables of list and list -d print the fixed workspace's profiles."""
    plain = _invoke_in_fixed_workspace(monkeypatch, tmp_path, ["list"])
    assert plain.exit_code == 0
    assert plain.stdout == LIST_OUTPUT

    detailed = runner.invoke(app, ["list", "-d"], env={"COLUMNS": "100"})
    assert detailed.exit_code == 0
    assert detailed.stdout == LIST_DETAILS_OUTPUT


def test_explain_command(monkeypatch, tmp_path):
    """The panel prints a profile with a role, volumes, usage and a dependency chain, and one without."""
    full = _invoke_in_fixed_workspace(monkeypatch, tmp_path, ["explain", "kafka-lite"])
    assert full.exit_code == 0
    assert full.stdout == EXPLAIN_KAFKA_LITE_OUTPUT

    bare = runner.invoke(app, ["explain", "valkey"], env={"COLUMNS": "100"})
    assert bare.exit_code == 0
    assert bare.stdout == EXPLAIN_VALKEY_OUTPUT


def test_explain_without_a_profile_is_a_usage_error():
    """A missing required argument exits 2 with a usage error, as Click reports it."""
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_ps_command(monkeypatch, tmp_path):
    """The container table prints sorted rows, the active profiles and a dash for what Docker leaves out."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: fake_containers()
    )

    result = _invoke_in_fixed_workspace(monkeypatch, tmp_path, ["ps", "--all"])

    assert result.exit_code == 0
    assert result.stdout == PS_ALL_OUTPUT


def test_explain_prints_the_host_address_note_once(monkeypatch, tmp_path):
    """Every explain panel ends with why host addresses use 127.0.0.1, not localhost."""
    from odctl.ui import HOST_ADDRESS_NOTE

    monkeypatch.chdir(tmp_path)  # no workspace, so the bundled registry is read
    result = runner.invoke(app, ["explain", "feast"])
    assert result.exit_code == 0
    # The note wraps inside the panel, so drop the borders before joining lines.
    text = " ".join(result.stdout.replace("│", " ").split())
    assert text.count(" ".join(HOST_ADDRESS_NOTE.split())) == 1
    assert "localhost:" not in text


def test_docker_not_running(monkeypatch):
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)
    result = runner.invoke(app, ["up", "kafka-lite"])
    assert result.exit_code != 0
    assert "Docker is not reachable" in result.stdout


def test_up_stops_when_the_images_for_the_tag_are_absent(monkeypatch):
    """A CLI version with no published images must say so, and start nothing."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.resolve_image_tag", lambda: "0.0.0-nope")
    monkeypatch.setattr(
        "odctl.main.find_unpublished_images",
        lambda plan: ["ghcr.io/jaehyeon-kim/odctl/deps:0.0.0-nope"],
    )
    mock_launch = MagicMock()
    monkeypatch.setattr("odctl.main.launch_stack", mock_launch)

    result = runner.invoke(app, ["up", "kafka-lite"])

    assert result.exit_code == 1
    assert "No published image for TAG=0.0.0-nope" in result.stdout
    assert "ghcr.io/jaehyeon-kim/odctl/deps:0.0.0-nope" in result.stdout
    assert ".odctl/.env" in result.stdout
    mock_launch.assert_not_called()


def test_up_dry_run_skips_the_image_preflight(monkeypatch):
    """A dry run reports the plan, so it must not need a registry."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    mock_preflight = MagicMock()
    monkeypatch.setattr("odctl.main.find_unpublished_images", mock_preflight)

    result = runner.invoke(app, ["up", "kafka-lite", "--dry-run"])

    assert result.exit_code == 0
    mock_preflight.assert_not_called()


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
    # The question of a teardown that names every profile reads them here.
    monkeypatch.setattr("odctl.docker.get_managed_containers", lambda plan: [])

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
    other_profile = fake_container("spark-master", "spark-master", "running", None, {})
    monkeypatch.setattr(
        "odctl.main.get_managed_containers", lambda plan: [other_profile]
    )
    # The question of a teardown that names every profile reads them here.
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: [other_profile]
    )

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
        "odctl.main.get_managed_containers", lambda plan: [mock_container]
    )
    monkeypatch.setattr(
        "odctl.main.get_stack_details",
        lambda f, p: _stack(["init-deps"], ["odctl-shared-deps"]),
    )

    result = runner.invoke(app, ["down", "--all", "-v"])

    assert result.exit_code == 0
    assert _stopped_files(mock_stop).count("compose-deps.yml") == 1


def _every_service_has_a_container(monkeypatch):
    """Give every packaged service a container, and fake stop_stack.

    `get_managed_containers` is faked to filter by the plan it is given, as the
    real one does, so `_teardown_of_all` and the idle check of deps run as written.
    """
    from odctl.planner import build_execution_plan

    def services(plan):
        return {s for f, p in plan.items() for s in get_stack_details(f, p).names}

    every = services(build_execution_plan(None, True, resolve_deps=False))
    containers = [fake_container(s, s, "running", None, {}) for s in sorted(every)]

    def managed(plan):
        wanted = services(plan)
        return [c for c in containers if c.name in wanted]

    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.get_managed_containers", managed)
    stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", stop)
    return stop


def _every_profile_but_deps():
    from odctl.planner import build_execution_plan

    plan = build_execution_plan(None, True, resolve_deps=False)
    return [p for profs in plan.values() for p in profs if p != "deps"]


def test_naming_every_profile_but_deps_removes_everything(monkeypatch):
    """A named teardown with `--volumes` removes deps once the rest is idle, so
    every profile but deps removes all that `--all --volumes` does. The MCP tool
    `down` accepted that call, because deps was compared on one side only."""
    from odctl.main import removes_everything

    _every_service_has_a_container(monkeypatch)

    assert removes_everything(_every_profile_but_deps())
    assert removes_everything(_every_profile_but_deps() + ["deps"])
    fewer = [p for p in _every_profile_but_deps() if p != "kafka-full"]
    assert not removes_everything(fewer)


def test_a_named_teardown_of_everything_asks_first(monkeypatch):
    """`down --all --volumes` asks, and naming every profile with `-v` removes the
    same data, so it asks the same question."""
    stop = _every_service_has_a_container(monkeypatch)
    asked = MagicMock(side_effect=typer_abort)
    monkeypatch.setattr("odctl.main.typer.confirm", asked)

    refused = runner.invoke(app, ["down", *_every_profile_but_deps(), "-v"])
    assert refused.exit_code == 1
    asked.assert_called_once()
    assert "WIPE ALL DATA" in asked.call_args.args[0]
    stop.assert_not_called()

    asked.reset_mock()
    confirmed = runner.invoke(app, ["down", *_every_profile_but_deps(), "-v", "--yes"])
    assert confirmed.exit_code == 0
    asked.assert_not_called()
    assert stop.called

    asked.reset_mock()
    assert runner.invoke(app, ["down", "kafka-lite", "-v"]).exit_code == 0
    asked.assert_not_called()


def typer_abort(*args, **kwargs):
    """Answer a prompt no, as `typer.confirm(..., abort=True)` does."""
    import click

    raise click.exceptions.Abort()


def test_naming_deps_keeps_the_shared_volume_while_others_run(monkeypatch):
    """The help of `--volumes` says the shared jar volume goes once no other
    profile uses it, but naming deps removed it while other profiles ran."""
    stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    other = fake_container("spark-master", "spark-master", "running", None, {})
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [other])

    result = runner.invoke(app, ["down", "deps", "-v"], env={"COLUMNS": "200"})

    assert result.exit_code == 0
    stop.assert_called_once_with("compose-deps.yml", ["deps"], remove_volumes=False)
    assert "odctl-shared-deps stays" in result.stdout

    stop.reset_mock()
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [])
    assert runner.invoke(app, ["down", "deps", "-v"]).exit_code == 0
    stop.assert_called_once_with("compose-deps.yml", ["deps"], remove_volumes=True)


def _down_all_mocks(monkeypatch):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    mock_container = MagicMock()
    mock_container.config.labels = {"com.docker.compose.service": "kafka"}
    monkeypatch.setattr(
        "odctl.main.get_managed_containers", lambda plan: [mock_container]
    )
    monkeypatch.setattr("odctl.main.get_stack_details", lambda f, p: _stack(["kafka"]))
    return mock_stop


def _no_prompt(*args, **kwargs):
    raise AssertionError("--yes must skip the prompt")


def test_down_all_volumes_yes_stops_without_a_prompt(monkeypatch):
    mock_stop = _down_all_mocks(monkeypatch)
    monkeypatch.setattr("odctl.main.typer.confirm", _no_prompt)

    result = runner.invoke(app, ["down", "--all", "-v", "--yes"])

    assert result.exit_code == 0
    mock_stop.assert_called()


def test_down_all_volumes_answered_no_stops_nothing(monkeypatch):
    mock_stop = _down_all_mocks(monkeypatch)

    result = runner.invoke(app, ["down", "--all", "-v"], input="n\n")

    assert result.exit_code == 1
    mock_stop.assert_not_called()


NOT_CHECKED = (
    ", only if no other profile has a container "
    "(Docker is not reachable, so this was not checked)"
)
UNNAMED_NOT_CHECKED = (
    "Remove Volume: the unnamed volumes of the stopped containers, if any "
    "(Docker is not reachable, so this was not checked)"
)
# The mounts of a container: two unnamed volumes with Docker's random names, a named
# volume and an external one that the spark file declares, and a bind mount.
SPARK_MOUNTS = [
    ("volume", "9f1c0a"),
    ("volume", "b27d44"),
    ("volume", "spark-events-data"),
    ("volume", "odctl-shared-deps"),
    ("bind", "/host/path"),
]
SPARK_VOLUMES = ["Remove Volume: spark-events-data", "Remove Volume: odctl-shared-deps"]


@pytest.mark.parametrize(
    "args, reachable, running, exit_code, named, not_named, in_order, missing",
    [
        pytest.param(
            ["spark-lite", "--volumes"],
            True,
            {"spark-master": SPARK_MOUNTS, "spark-history": []},
            0,
            [*SPARK_VOLUMES, "Remove Volume: 2 unnamed volume(s) of spark-master"],
            ["of spark-history", "9f1c0a"],
            [
                "compose-spark.yml",
                "Remove Volume: spark-events-data",
                "Remove Volume: 2 unnamed volume(s) of spark-master",
                "compose-deps.yml",
                "Remove Volume: odctl-shared-deps",
            ],
            set(),
            id="shared volume when no other profile has a container",
        ),
        pytest.param(
            ["spark-lite", "--volumes"],
            True,
            {"spark-master": SPARK_MOUNTS, "kafka": []},
            0,
            ["Remove Volume: spark-events-data", "of spark-master"],
            ["odctl-shared-deps", "compose-deps.yml"],
            [],
            set(),
            id="shared volume kept while another profile has a container",
        ),
        pytest.param(
            ["spark-lite", "--volumes"],
            False,
            {},
            0,
            [
                "Remove Volume: spark-events-data",
                "Stop Profile: deps" + NOT_CHECKED,
                "Remove Volume: odctl-shared-deps" + NOT_CHECKED,
                UNNAMED_NOT_CHECKED,
            ],
            [],
            [
                "compose-spark.yml",
                "Remove Volume: spark-events-data",
                UNNAMED_NOT_CHECKED,
                "compose-deps.yml",
                "Stop Profile: deps",
                "Remove Volume: odctl-shared-deps",
            ],
            set(),
            id="shared volume and unnamed volumes not checked without Docker",
        ),
        pytest.param(
            ["spark-lite", "--volumes"],
            True,
            {},
            0,
            SPARK_VOLUMES,
            ["unnamed volume"],
            [],
            set(),
            id="no unnamed line for a file with no container",
        ),
        pytest.param(
            ["spark-lite", "--volumes"],
            True,
            {"spark-master": SPARK_MOUNTS},
            0,
            ["of spark-master"],
            ["Remove Volume: spark-events-data"],
            [],
            {"spark-events-data"},
            id="a named volume that does not exist is not listed",
        ),
        pytest.param(
            ["--all", "--volumes"],
            True,
            {"kafka": [("volume", "5e5e5e")], "init-deps": [("volume", "aaaaaa")]},
            0,
            [
                "Remove Volume: odctl-shared-deps",
                "Remove Volume: 1 unnamed volume(s) of kafka",
            ],
            ["of init-deps"],
            ["compose-deps.yml", "Remove Volume: odctl-shared-deps"],
            set(),
            id="all removes the shared volume and never lists unnamed volumes for deps",
        ),
        pytest.param(
            ["--all"],
            False,
            {},
            1,
            ["Docker is not reachable."],
            ["Dry Run"],
            [],
            set(),
            id="all needs Docker",
        ),
        pytest.param(
            ["spark-lite"],
            False,
            {},
            0,
            ["Stop Profile: spark-lite"],
            ["Remove Volume"],
            [],
            set(),
            id="no volumes without --volumes",
        ),
    ],
)
def test_down_dry_run_names_the_volumes(
    monkeypatch,
    args,
    reachable,
    running,
    exit_code,
    named,
    not_named,
    in_order,
    missing,
):
    """The dry run names the named volumes the real run removes, by the rule it uses,
    adds a line with the number of unnamed volumes for each container that has any,
    read from the container's mounts, and stops nothing. A named teardown without
    --volumes needs no Docker."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: reachable)
    containers = [
        fake_container(s, s, "running", None, {}, mounts)
        for s, mounts in running.items()
    ]

    def containers_of(plan):
        services = {
            s for f, profs in plan.items() for s in get_stack_details(f, profs).names
        }
        return [
            c
            for c in containers
            if c.config.labels["com.docker.compose.service"] in services
        ]

    monkeypatch.setattr("odctl.main.get_managed_containers", containers_of)
    monkeypatch.setattr(
        "odctl.main.get_volume_names",
        lambda: {"spark-events-data", "odctl-shared-deps"} - missing,
    )

    result = runner.invoke(app, ["down", *args, "--dry-run"], env={"COLUMNS": "200"})

    assert result.exit_code == exit_code
    for text in named:
        assert text in result.stdout
    for text in not_named:
        assert text not in result.stdout
    positions = [result.stdout.index(text) for text in in_order]
    assert positions == sorted(positions)
    mock_stop.assert_not_called()


@pytest.mark.parametrize("volumes", [["-v"], []], ids=["volumes", "no volumes"])
def test_down_deps_dry_run_without_docker_stops_deps_in_every_case(
    monkeypatch, volumes
):
    """The real run stops a named deps whatever else runs; only its shared jar
    volume waits until no other profile has a container."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)

    result = runner.invoke(
        app, ["down", "deps", *volumes, "--dry-run"], env={"COLUMNS": "200"}
    )

    assert result.exit_code == 0, result.stdout
    lines = [line.strip() for line in result.stdout.splitlines()]
    assert any(line.endswith("Stop Profile: deps") for line in lines), lines
    volume = "Remove Volume: odctl-shared-deps" + NOT_CHECKED
    assert any(line.endswith(volume) for line in lines) == bool(volumes), lines
    mock_stop.assert_not_called()


def test_mcp_without_the_extra_names_the_install(monkeypatch):
    """The CLI runs without the mcp package, and `odctl mcp` says how to install it, on
    stderr like every message of `odctl mcp`."""
    # A submodule of mcp that an earlier test imported would still import.
    for name in [n for n in sys.modules if n == "mcp" or n.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "mcp", None)
    monkeypatch.delitem(sys.modules, "odctl.mcp_server", raising=False)

    result = runner.invoke(app, ["mcp"])

    assert result.exit_code == 1
    assert 'uv tool install "odctl[mcp]"' in result.stderr


def test_init_force_yes_replaces_the_workspace_without_a_prompt(tmp_path, monkeypatch):
    (tmp_path / ".odctl").mkdir()
    monkeypatch.setattr("odctl.main.get_workspace_dir", lambda: tmp_path / ".odctl")
    mock_init = MagicMock()
    monkeypatch.setattr("odctl.main.init_workspace", mock_init)
    monkeypatch.setattr("odctl.main.typer.confirm", _no_prompt)

    result = runner.invoke(app, ["init", "--force", "-y"])

    assert result.exit_code == 0
    mock_init.assert_called_once_with(force=True)


def test_init_force_answered_no_keeps_the_workspace(tmp_path, monkeypatch):
    """`init --force` answered `n` aborts and leaves the workspace as it is."""
    mock_init = MagicMock()
    monkeypatch.setattr("odctl.main.init_workspace", mock_init)
    workspace = tmp_path / ".odctl"
    workspace.mkdir()
    monkeypatch.setattr("odctl.main.get_workspace_dir", lambda: workspace)

    result = runner.invoke(app, ["init", "--force"], input="n\n")

    assert result.exit_code == 1
    mock_init.assert_not_called()


def test_init_refuses_a_folder_that_is_not_a_workspace(tmp_path):
    """`init --force` removed whatever folder `--workspace` named, with every file
    in it. A folder that holds files and no registry.yml is not a workspace."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "notes.txt").write_text("my work")

    result = runner.invoke(
        app, ["-w", str(project), "init", "--force", "--yes"], env={"COLUMNS": "500"}
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert f"{project} is not an odctl workspace" in result.stdout
    assert (project / "notes.txt").read_text() == "my work"


def test_init_refuses_a_file(tmp_path):
    """A file named by `--workspace` ended `init` in NotADirectoryError."""
    target = tmp_path / "afile"
    target.write_text("x")

    for args in (["init"], ["init", "--force", "--yes"]):
        result = runner.invoke(app, ["-w", str(target), *args], env={"COLUMNS": "500"})
        assert result.exit_code == 1, args
        assert isinstance(result.exception, SystemExit), args
        assert f"{target} is a file" in result.stdout, args
    assert target.read_text() == "x"


def test_init_force_replaces_a_workspace_and_names_it_in_the_prompt(tmp_path):
    workspace = tmp_path / "ws"
    assert runner.invoke(app, ["-w", str(workspace), "init"]).exit_code == 0
    (workspace / "compose-kafka.yml").write_text("edited")

    asked = runner.invoke(
        app,
        ["-w", str(workspace), "init", "--force"],
        input="n\n",
        env={"COLUMNS": "500"},
    )
    assert asked.exit_code == 1
    assert str(workspace) in asked.stdout
    assert (workspace / "compose-kafka.yml").read_text() == "edited"

    replaced = runner.invoke(app, ["-w", str(workspace), "init", "--force", "--yes"])
    assert replaced.exit_code == 0
    assert (workspace / "compose-kafka.yml").read_text() != "edited"


@pytest.mark.parametrize(
    "args, workspace_exists",
    [
        pytest.param(["init", "--force"], True, id="init"),
        pytest.param(["down", "--all", "--volumes"], False, id="down"),
    ],
)
def test_confirmation_with_no_input_aborts(
    args, workspace_exists, tmp_path, monkeypatch
):
    """With no terminal and no `--yes`, the prompt reads end of input and aborts."""
    mock_stop = _down_all_mocks(monkeypatch)
    mock_init = MagicMock()
    monkeypatch.setattr("odctl.main.init_workspace", mock_init)
    workspace = tmp_path / ".odctl"
    if workspace_exists:
        workspace.mkdir()
    monkeypatch.setattr("odctl.main.get_workspace_dir", lambda: workspace)

    result = runner.invoke(app, args, input="")

    assert result.exit_code == 1
    mock_init.assert_not_called()
    mock_stop.assert_not_called()


def test_dry_run_names_a_volume_by_its_docker_name(monkeypatch):
    """A service mounts a volume by its key, and its `name:` can differ, so the dry run
    lists the name Docker removes, and a mount of it is not counted as unnamed."""
    from odctl import main

    plan = {"compose-spark.yml": ["spark-lite"]}
    monkeypatch.setattr(main, "is_docker_running", lambda: True)
    monkeypatch.setattr(
        main, "get_stack_details", lambda f, p: _stack(["spark"], ["events"])
    )
    monkeypatch.setattr(
        main, "get_declared_volumes", lambda f: {"events": "custom-event-data"}
    )
    monkeypatch.setattr(main, "get_volume_names", lambda: {"custom-event-data"})
    mount = SimpleNamespace(type="volume", name="custom-event-data")
    container = SimpleNamespace(name="spark", mounts=[mount])
    monkeypatch.setattr(main, "get_managed_containers", lambda p: [container])

    assert main._dry_run_volumes(plan, reachable=True) == {
        "compose-spark.yml": ["custom-event-data"]
    }


@pytest.mark.parametrize(
    "names, volumes, idle, expected",
    [
        (["deps-extra"], ["-v"], False, (["deps-extra"], False)),
        (["deps", "deps-extra"], [], False, (["deps", "deps-extra"], False)),
        (["deps-extra"], ["-v"], True, (["deps", "deps-extra"], True)),
    ],
    ids=["extra, others run", "deps and extra", "extra, nothing else runs"],
)
def test_down_stops_every_named_profile_of_the_deps_file(
    monkeypatch, names, volumes, idle, expected
):
    """A workspace can add a profile such as deps-extra to compose-deps.yml, and the
    teardown dropped it with deps. It follows deps' rule for volumes, because
    `down --volumes` on that file removes every volume the file declares."""
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.main.removes_everything", lambda profiles: False)
    monkeypatch.setattr(
        "odctl.main.build_execution_plan",
        lambda profiles, all, resolve_deps: {"compose-deps.yml": list(profiles)},
    )
    monkeypatch.setattr("odctl.main.expand_plan_dependencies", lambda plan: plan)
    monkeypatch.setattr("odctl.main._shared_deps_are_idle", lambda plan: idle)

    result = runner.invoke(app, ["down", *names, *volumes])

    assert result.exit_code == 0, result.stdout
    assert [
        (c.args[0], c.args[1], c.kwargs["remove_volumes"])
        for c in mock_stop.call_args_list
    ] == [("compose-deps.yml", expected[0], expected[1])]


def test_down_dry_run_lists_the_other_profiles_of_the_deps_file(monkeypatch):
    monkeypatch.setattr("odctl.main.stop_stack", MagicMock())
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)
    monkeypatch.setattr(
        "odctl.main.build_execution_plan",
        lambda profiles, all, resolve_deps: {"compose-deps.yml": list(profiles)},
    )
    monkeypatch.setattr("odctl.main.expand_plan_dependencies", lambda plan: plan)

    result = runner.invoke(
        app, ["down", "deps", "deps-extra", "--dry-run"], env={"COLUMNS": "200"}
    )

    assert result.exit_code == 0, result.stdout
    lines = [line.strip() for line in result.stdout.splitlines()]
    assert "└─ 💥 Stop Profile: deps" in lines, lines
    assert "└─ 💥 Stop Profile: deps-extra" in lines, lines


@pytest.mark.parametrize("idle", [True, False])
def test_down_dry_run_lists_the_volumes_of_the_deps_files_other_profiles(
    monkeypatch, idle
):
    """`down deps-extra -v` on an idle stack removes the deps file's volumes, deps-extra's
    included, so the dry run lists them; with other profiles running it removes none."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr(
        "odctl.main.build_execution_plan",
        lambda profiles, all, resolve_deps: {"compose-deps.yml": list(profiles)},
    )
    monkeypatch.setattr("odctl.main.expand_plan_dependencies", lambda plan: plan)
    monkeypatch.setattr("odctl.main._shared_deps_are_idle", lambda plan: idle)
    monkeypatch.setattr(
        "odctl.main.get_declared_volumes",
        lambda file: {
            "shared-deps": "odctl-shared-deps",
            "extra-data": "odctl_extra-data",
        },
    )
    monkeypatch.setattr(
        "odctl.main.get_volume_names", lambda: {"odctl-shared-deps", "odctl_extra-data"}
    )

    def details(file, profiles):
        keys = {"deps": ["shared-deps"], "deps-extra": ["extra-data"]}
        return _stack([], [k for p in profiles for k in keys.get(p, [])])

    monkeypatch.setattr("odctl.main.get_stack_details", details)

    result = runner.invoke(
        app, ["down", "deps-extra", "-v", "--dry-run"], env={"COLUMNS": "200"}
    )

    assert result.exit_code == 0, result.stdout
    assert ("odctl_extra-data" in result.stdout) is idle, result.stdout
    assert ("odctl-shared-deps" in result.stdout) is idle, result.stdout
