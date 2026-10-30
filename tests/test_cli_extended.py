import sys

import pytest
from unittest.mock import MagicMock
from typer.testing import CliRunner
from odctl.docker import get_stack_details
from odctl.main import app
from cli_workspace import fake_container, fake_containers, write_workspace

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
│   📦 valkey                 (valkey/valkey:8)                                                    │
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


def _down_all_mocks(monkeypatch):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    mock_container = MagicMock()
    mock_container.config.labels = {"com.docker.compose.service": "kafka"}
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: [mock_container]
    )
    monkeypatch.setattr(
        "odctl.docker.get_stack_details", lambda f, p: (["kafka"], [], [], [])
    )
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
            s for f, profs in plan.items() for s in get_stack_details(f, profs)[0]
        }
        return [
            c
            for c in containers
            if c.config.labels["com.docker.compose.service"] in services
        ]

    monkeypatch.setattr("odctl.main.get_managed_containers", containers_of)
    monkeypatch.setattr("odctl.docker.get_managed_containers", containers_of)
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
