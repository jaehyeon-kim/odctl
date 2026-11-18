import json
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from cli_workspace import fake_container, fake_containers, write_workspace
from odctl import ui
from odctl.main import app

runner = CliRunner()

PORT_KEYS = {"host", "container", "protocol"}
SERVICE_KEYS = {"name", "image", "ports"}
PROFILE_KEYS = {
    "profile",
    "stack",
    "description",
    "compose_file",
    "depends_on",
    "starts",
    "services",
}


def _fixed_workspace(monkeypatch, tmp_path):
    """Use the fixed registry and compose files from tests/cli_workspace.py."""
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)


def _running_containers(monkeypatch):
    """Make Docker reachable and give `ps` the fixed containers."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: fake_containers()
    )


def _table_first_cells(text):
    """The first cell of every body row of a Rich table."""
    return [
        line.split("│")[1].strip()
        for line in text.splitlines()
        if line.startswith("│") and line.split("│")[1].strip()
    ]


def test_list_json_has_the_documented_keys(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)

    result = runner.invoke(app, ["list", "--json"])

    assert result.exit_code == 0
    profiles = json.loads(result.stdout)
    assert [p["profile"] for p in profiles] == [
        "base",
        "kafka-full",
        "kafka-lite",
        "valkey",
    ]
    by_name = {p["profile"]: p for p in profiles}
    for entry in profiles:
        assert set(entry) == PROFILE_KEYS
        for service in entry["services"]:
            assert set(service) == SERVICE_KEYS
            for port in service["ports"]:
                assert set(port) == PORT_KEYS
    lite = by_name["kafka-lite"]
    assert lite["stack"] == "streaming"
    assert lite["depends_on"] == ["base"]
    assert lite["starts"] == ["base", "kafka-lite"]
    assert by_name["valkey"]["starts"] == ["base", "kafka-lite", "valkey"]
    assert [s["name"] for s in lite["services"]] == ["kafka", "kafka-ui"]
    assert lite["services"][0]["ports"] == [
        {"host": 9092, "container": 9092, "protocol": "tcp"}
    ]
    assert by_name["valkey"]["services"][0]["ports"][1]["protocol"] == "udp"


def test_list_json_includes_services_without_details(monkeypatch, tmp_path):
    """A script does not need -d to get the services."""
    _fixed_workspace(monkeypatch, tmp_path)

    plain = json.loads(runner.invoke(app, ["list", "--json"]).stdout)
    detailed = json.loads(runner.invoke(app, ["list", "--json", "-d"]).stdout)

    assert plain == detailed
    assert plain[0]["services"][0]["name"] == "init-base"


def test_explain_json_adds_usage_role_and_volumes(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)

    result = runner.invoke(app, ["explain", "kafka-lite", "--json"])

    assert result.exit_code == 0
    details = json.loads(result.stdout)
    assert set(details) == PROFILE_KEYS | {"usage", "role", "volumes"}
    listed = next(
        p
        for p in json.loads(runner.invoke(app, ["list", "--json"]).stdout)
        if p["profile"] == "kafka-lite"
    )
    assert {k: details[k] for k in PROFILE_KEYS} == listed
    assert details["usage"].startswith("Dashboard: http://127.0.0.1:8086")
    assert details["role"] == "A broker with a dashboard."
    assert details["volumes"] == ["ui-data"]


def test_explain_json_without_usage_is_null(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)

    details = json.loads(runner.invoke(app, ["explain", "valkey", "--json"]).stdout)

    assert details["usage"] is None
    assert details["role"] is None
    assert details["volumes"] == []


def test_ps_json_has_the_documented_keys(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)
    _running_containers(monkeypatch)

    result = runner.invoke(app, ["ps", "--all", "--json"])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert set(report) == {"active_profiles", "containers"}
    assert report["active_profiles"] == ["base", "kafka-lite"]
    assert [c["name"] for c in report["containers"]] == [
        "init-base",
        "kafka",
        "kafka-ui",
        "odd",
    ]
    for container in report["containers"]:
        assert set(container) == {"name", "service", "state", "health", "ports"}
    by_name = {c["name"]: c for c in report["containers"]}
    assert by_name["kafka"]["ports"] == [
        {"host": 9092, "container": 9092, "protocol": "tcp"}
    ]
    assert by_name["kafka"]["health"] == "starting"
    assert by_name["init-base"]["health"] is None
    assert by_name["odd"]["service"] is None
    assert by_name["odd"]["ports"] == []


def test_info_json_has_the_documented_keys(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "1.2.3")
    monkeypatch.setattr("odctl.docker.is_docker_running", lambda: True)
    monkeypatch.setattr(
        "odctl.docker.image_is_local", lambda reference: "/deps:" in reference
    )

    result = runner.invoke(app, ["info", "--json"])

    assert result.exit_code == 0
    info = json.loads(result.stdout)
    assert set(info) == {"cli_version", "tag", "workspace", "docker", "images"}
    assert info["cli_version"] == "1.2.3"
    assert info["tag"] == "1.2.3"
    assert info["workspace"] == {
        "path": str(tmp_path / ".odctl"),
        "exists": False,
        "stale_tag": None,
    }
    assert info["docker"] == {"reachable": True}
    references = [image["reference"] for image in info["images"]]
    assert references == sorted(references)
    assert references
    assert all(r.startswith("ghcr.io/jaehyeon-kim/odctl/") for r in references)
    assert all(r.endswith(":1.2.3") for r in references)
    for image in info["images"]:
        assert set(image) == {"reference", "local"}
        assert image["local"] == ("/deps:" in image["reference"])


def test_info_json_without_docker_lists_no_image_as_local(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("odctl.docker.is_docker_running", lambda: False)
    monkeypatch.setattr("odctl.docker.image_is_local", lambda reference: True)

    info = json.loads(runner.invoke(app, ["info", "--json"]).stdout)

    assert info["docker"] == {"reachable": False}
    assert info["images"]
    assert not any(image["local"] for image in info["images"])


def test_warnings_go_to_stderr_with_json(monkeypatch, tmp_path):
    """With an old workspace, stdout still holds only the JSON document."""
    _fixed_workspace(monkeypatch, tmp_path)
    (tmp_path / ".odctl" / ".env").write_text("TAG=0.7.0\n")
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "0.8.0")
    _running_containers(monkeypatch)

    for args in (["list"], ["explain", "valkey"], ["ps", "--all"], ["info"]):
        result = runner.invoke(app, [*args, "--json"])

        assert result.exit_code == 0, args
        json.loads(result.stdout)
        assert "TAG=0.7.0" in result.stderr, args

    info = json.loads(runner.invoke(app, ["info", "--json"]).stdout)
    assert info["workspace"]["stale_tag"] == "0.7.0"


def test_errors_stay_on_stdout_after_a_json_command(monkeypatch, tmp_path, capsys):
    """The stderr switch ends with the invocation, so a later error prints to stdout."""
    _fixed_workspace(monkeypatch, tmp_path)

    runner.invoke(app, ["list", "--json"])
    capsys.readouterr()
    ui.print_error("after the command")

    captured = capsys.readouterr()
    assert "after the command" in captured.out
    assert captured.err == ""


def test_errors_go_to_stderr_with_json(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)

    unknown_profile = runner.invoke(app, ["explain", "nope", "--json"])
    unknown_ps_profile = runner.invoke(app, ["ps", "nope", "--json"])
    no_profile = runner.invoke(app, ["ps", "--json"])
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)
    no_docker = runner.invoke(app, ["ps", "--all", "--json"])

    for result, message in (
        (unknown_profile, "Profile 'nope' not found in registry."),
        (unknown_ps_profile, "Unknown profiles: nope"),
        (no_profile, "Please specify profile names or use --all"),
        (no_docker, "Docker is not reachable."),
    ):
        assert result.exit_code == 1
        assert result.stdout == ""
        assert message in result.stderr


def test_table_and_json_list_the_same_profiles_and_containers(monkeypatch, tmp_path):
    _fixed_workspace(monkeypatch, tmp_path)
    _running_containers(monkeypatch)
    wide = {"COLUMNS": "100"}

    table = runner.invoke(app, ["list"], env=wide).stdout
    profiles = json.loads(runner.invoke(app, ["list", "--json"]).stdout)
    assert sorted(_table_first_cells(table)) == [p["profile"] for p in profiles]

    table = runner.invoke(app, ["ps", "--all"], env=wide).stdout
    report = json.loads(runner.invoke(app, ["ps", "--all", "--json"]).stdout)
    assert _table_first_cells(table) == [c["name"] for c in report["containers"]]
    assert f"Active Profiles: {', '.join(report['active_profiles'])}" in table


def _write_compose_cache(tmp_path, text):
    """Replace the fixed workspace's cache compose file."""
    (tmp_path / ".odctl" / "compose-cache.yml").write_text(text)


def _failed_with(result, message):
    """Check that a command stopped with exit 1 and the message, not a traceback."""
    printed = result.stdout + result.stderr
    assert result.exit_code == 1, printed
    assert isinstance(result.exception, SystemExit), result.exception
    assert message in printed, printed


def _no_containers(monkeypatch):
    """Make Docker reachable, with no container and no volume, and make every
    compose client a fake, so a command that gets past its first file runs no
    `docker compose`."""
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    client = MagicMock()
    client.container.list.return_value = []
    client.volume.list.return_value = []
    monkeypatch.setattr("odctl.docker.client", client)
    monkeypatch.setattr("odctl.docker.DockerClient", MagicMock())


# Every command path that reads the compose file of `valkey`, with Docker faked.
COMMANDS_READING_COMPOSE = [
    ["list", "-d"],
    ["list", "--json"],
    ["explain", "valkey"],
    ["explain", "valkey", "--json"],
    ["ps", "valkey"],
    ["ps", "valkey", "--json"],
    ["info", "--json"],
    ["up", "valkey"],
    ["down", "valkey"],
    ["down", "valkey", "-v", "--dry-run"],
    ["down", "--all", "-v", "--yes"],
    ["pull", "valkey"],
    ["logs", "valkey"],
    ["logs", "valkey", "--service", "valkey"],
    ["restart", "valkey"],
    ["recreate", "valkey"],
]


@pytest.mark.parametrize(
    "compose, reason",
    [
        (None, "the file does not exist"),
        ("services: [\n", "it is not valid YAML"),
        (b"services:\n  valkey:\n    image: caf\xe9\n", "it is not UTF-8 text"),
    ],
    ids=["missing", "invalid", "not UTF-8"],
)
@pytest.mark.parametrize("args", COMMANDS_READING_COMPOSE, ids=" ".join)
def test_an_unreadable_compose_file_stops_every_command(
    monkeypatch, tmp_path, compose, reason, args
):
    """Each command says which file it cannot read and why, and exits 1. Before
    1.10.0 the tables listed `File Error` or `Err: <type>` as the file's services and
    exited 0, and `down -v --dry-run`, `up` and `info --json` ended in a traceback
    or left the file out."""
    _fixed_workspace(monkeypatch, tmp_path)
    _no_containers(monkeypatch)
    cache = tmp_path / ".odctl" / "compose-cache.yml"
    if compose is None:
        cache.unlink()
    elif isinstance(compose, bytes):
        cache.write_bytes(compose)
    else:
        cache.write_text(compose)

    result = runner.invoke(app, args, env={"COLUMNS": "500"})

    _failed_with(result, f"Cannot read compose-cache.yml: {reason}")
    if "--json" in args:
        assert result.stdout == ""


def test_ports_are_raw_in_the_tables_and_expanded_in_json(monkeypatch, tmp_path):
    """The tables print each port as the compose file wrote it; the JSON keeps plain numbers."""
    _fixed_workspace(monkeypatch, tmp_path)
    monkeypatch.delenv("VK_PORT", raising=False)
    _write_compose_cache(
        tmp_path,
        """\
services:
  valkey:
    image: valkey/valkey:8
    ports:
      - "${VK_PORT:-6379}:6379"
      - "7000-7001:7000-7001"
      - "6380:6380/tcp"
      - "9000"
      - target: 9001
        published: 9001
        protocol: udp
    profiles: [valkey]
""",
    )

    listed = runner.invoke(app, ["list", "-d"], env={"COLUMNS": "200"}).stdout
    explained = runner.invoke(app, ["explain", "valkey"], env={"COLUMNS": "100"}).stdout
    assert "valkey:${VK_PORT:-6379}:6379" in listed
    assert "valkey:7000-7001:7000-7001" in listed
    assert "valkey:6380:6380/tcp" in listed
    assert "valkey:9000" in listed
    assert "valkey:9001:9001/udp" in listed
    # The panel prints the ports the JSON holds: expanded, with no range, no port
    # without a host part, and the protocol only when it is not tcp.
    assert "Host 6379  → Container valkey:6379" in explained
    assert "Host 6380  → Container valkey:6380 " in explained
    assert "6380/tcp" not in explained
    assert "Host 9001  → Container valkey:9001/udp" in explained
    assert "7000" not in explained
    assert "Host 9000" not in explained

    for args in (["list", "--json"], ["explain", "valkey", "--json"]):
        output = json.loads(runner.invoke(app, args).stdout)
        entry = output if isinstance(output, dict) else output[-1]
        assert entry["services"][0]["ports"] == [
            {"host": 6379, "container": 6379, "protocol": "tcp"},
            {"host": 6380, "container": 6380, "protocol": "tcp"},
            {"host": 9001, "container": 9001, "protocol": "udp"},
        ]

    monkeypatch.setenv("VK_PORT", "7777")
    expanded = json.loads(runner.invoke(app, ["explain", "valkey", "--json"]).stdout)
    assert expanded["services"][0]["ports"][1] == {
        "host": 7777,
        "container": 6379,
        "protocol": "tcp",
    }


@pytest.mark.parametrize(
    "old, new, message",
    [
        (
            "valkey: [kafka-lite]",
            "valkey: [kafka-lit]",
            "the profile 'valkey' depends on 'kafka-lit', which no stack lists",
        ),
        (
            "profiles: [valkey]",
            "profiles: [valkey, base]",
            "the profile 'base' is listed under the stacks 'base' and 'cache'",
        ),
        (
            "profiles: [valkey]",
            "profiles: [valkey, valkey]",
            "the stack 'cache' lists the profile 'valkey' twice",
        ),
        (
            "      valkey: [kafka-lite]",
            "      valkey: [kafka-lite]\n      kafka-lite: [base]",
            "the stack 'cache' lists dependencies for 'kafka-lite', which is not one of its profiles",
        ),
    ],
    ids=[
        "unknown dependency",
        "profile in two stacks",
        "profile twice in one stack",
        "key of another stack",
    ],
)
def test_a_registry_whose_profiles_do_not_resolve_stops_every_command(
    monkeypatch, tmp_path, old, new, message
):
    """The registry is checked when it loads, so every command names the entry and
    exits 1. Before 1.10.0 an unknown dependency raised KeyError from `up`, and the
    other two loaded and planned the wrong files."""
    _fixed_workspace(monkeypatch, tmp_path)
    registry = tmp_path / ".odctl" / "registry.yml"
    assert old in registry.read_text()
    registry.write_text(registry.read_text().replace(old, new))

    for args in (["list"], ["explain", "valkey"], ["up", "valkey", "--dry-run"]):
        result = runner.invoke(app, args, env={"COLUMNS": "500"})
        _failed_with(result, message)


def test_usage_for_other_profiles_is_null_in_json_and_a_placeholder_in_the_panel(
    monkeypatch, tmp_path
):
    """A stack that gives usage for some profiles shows the placeholder for the rest only in the panel."""
    _fixed_workspace(monkeypatch, tmp_path)
    registry = tmp_path / ".odctl" / "registry.yml"
    registry.write_text(
        registry.read_text().replace("      kafka-full: Three brokers.\n", "")
    )

    details = json.loads(runner.invoke(app, ["explain", "kafka-full", "--json"]).stdout)
    panel = runner.invoke(app, ["explain", "kafka-full"], env={"COLUMNS": "100"})

    assert details["usage"] is None
    assert "No specific usage guide for profile: kafka-full" in panel.stdout


def test_neighbouring_stacks_with_the_same_text_stay_separate_groups(
    monkeypatch, tmp_path
):
    """The table groups profiles by the registry's stack, not by what the stacks say."""
    _fixed_workspace(monkeypatch, tmp_path)
    registry = tmp_path / ".odctl" / "registry.yml"
    registry.write_text(
        registry.read_text()
        .replace(
            "description: An in-memory cache.",
            "description: Event streaming for the tests.",
        )
        .replace("file: compose-cache.yml", "file: compose-kafka.yml")
    )

    table = runner.invoke(app, ["list"], env={"COLUMNS": "100"}).stdout

    assert table.count("Event streaming for the tests.") == 2
    # One Parent Stack cell per group.
    assert table.count("│ streaming ") == 2


def test_ps_json_sorts_ports_and_the_table_keeps_dockers_order(monkeypatch, tmp_path):
    """The attribute keeps Docker's order; only the JSON sorts."""
    _fixed_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    unsorted = fake_container(
        "kafka",
        "kafka",
        "running",
        None,
        {
            "9092/tcp": [{"HostIp": "127.0.0.1", "HostPort": "9092"}],
            "80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}],
        },
    )
    monkeypatch.setattr("odctl.docker.get_managed_containers", lambda plan: [unsorted])

    report = json.loads(runner.invoke(app, ["ps", "--all", "--json"]).stdout)
    table = runner.invoke(app, ["ps", "--all"], env={"COLUMNS": "100"}).stdout

    assert [p["host"] for p in report["containers"][0]["ports"]] == [8080, 9092]
    assert table.index("9092 → 9092/tcp") < table.index("8080 → 80/tcp")


# Every command path that loads the registry, with Docker faked.
COMMANDS_READING_THE_REGISTRY = [
    ["list"],
    ["list", "--json"],
    ["explain", "kafka-lite"],
    ["ps", "--all"],
    ["info", "--json"],
    ["up", "kafka-lite", "--dry-run"],
    ["down", "kafka-lite", "--dry-run"],
    ["down", "--all"],
    ["pull", "kafka-lite"],
    ["logs", "kafka-lite"],
    ["restart", "kafka-lite"],
    ["recreate", "kafka-lite"],
]


@pytest.mark.parametrize(
    "registry, reason",
    [
        (None, "the file does not exist"),
        ("stacks: [\n", "it is not valid YAML"),
        ("", "its top level is not a mapping"),
        (
            "stacks:\n  kafka:\n    file: compose-kafka.yml\n",
            "stacks.kafka.description",
        ),
        (b"stacks:\n  caf\xe9: {}\n", "it is not UTF-8 text"),
    ],
    ids=["missing", "invalid", "empty", "incomplete", "not UTF-8"],
)
@pytest.mark.parametrize("args", COMMANDS_READING_THE_REGISTRY, ids=" ".join)
def test_an_unreadable_registry_stops_every_command(
    monkeypatch, tmp_path, registry, reason, args
):
    """A workspace with a registry.yml that is missing, not valid YAML, empty or not
    a registry gives a message naming the file and exit 1, not a traceback. An empty
    `.odctl/` folder, or `--workspace` naming a folder with no registry, is the
    missing case."""
    _fixed_workspace(monkeypatch, tmp_path)
    _no_containers(monkeypatch)
    path = tmp_path / ".odctl" / "registry.yml"
    if registry is None:
        path.unlink()
    elif isinstance(registry, bytes):
        path.write_bytes(registry)
    else:
        path.write_text(registry)

    result = runner.invoke(app, args, env={"COLUMNS": "500"})

    _failed_with(result, f"Cannot read {path}: {reason}")
    if "--json" in args:
        assert result.stdout == ""


@pytest.mark.parametrize(
    "target, args",
    [
        ("odctl.main.build_execution_plan", ["restart", "kafka-lite"]),
        ("odctl.reports.build_info", ["info"]),
        ("odctl.planner.read_compose", ["up", "kafka-lite", "--dry-run"]),
    ],
    ids=["decorated command", "info", "unreachable profile check"],
)
def test_a_value_error_from_a_bug_is_not_reported_as_a_file_error(
    monkeypatch, tmp_path, target, args
):
    """Only a file that cannot be read becomes a message and exit 1, or is skipped by
    the check for unreachable profiles; any other ValueError raises as itself, so a
    bug shows its traceback."""
    _fixed_workspace(monkeypatch, tmp_path)
    _no_containers(monkeypatch)

    def bug(*args, **kwargs):
        raise ValueError("a bug")

    monkeypatch.setattr(target, bug)

    result = runner.invoke(app, args)

    assert isinstance(result.exception, ValueError), result.exception
    assert "a bug" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["up", "valkey", "--dry-run"],
        ["down", "valkey", "--dry-run"],
        ["restart", "valkey"],
        ["recreate", "valkey"],
    ],
    ids=" ".join,
)
def test_registry_names_are_printed_as_written(monkeypatch, tmp_path, args):
    """The dry run and the progress lines print the registry's file and profile
    names through the same escaping as `list` and `explain`."""
    _fixed_workspace(monkeypatch, tmp_path)
    _no_containers(monkeypatch)
    monkeypatch.setattr("odctl.projects.create_client", lambda *a, **kw: MagicMock())
    monkeypatch.setattr("odctl.projects.wait_for_one_shot_containers", lambda: None)
    workspace = tmp_path / ".odctl"
    (workspace / "compose-cache.yml").rename(workspace / "compose-[bold]cache.yml")
    registry = workspace / "registry.yml"
    registry.write_text(
        registry.read_text().replace(
            "file: compose-cache.yml", "file: compose-[bold]cache.yml"
        )
    )

    result = runner.invoke(app, args, env={"COLUMNS": "200"})

    assert result.exit_code == 0, (result.stdout, result.exception)
    assert "compose-[bold]cache.yml" in result.stdout, result.stdout


def test_compose_names_are_printed_as_written(monkeypatch, tmp_path):
    """`list -d` prints the services and ports and `explain` the volumes as the
    compose file names them."""
    _fixed_workspace(monkeypatch, tmp_path)
    _write_compose_cache(
        tmp_path,
        """\
services:
  valkey[bold]x:
    image: valkey/valkey-bundle:9
    ports:
      - "127.0.0.1:${VK_PORT:-6379}:6379[bold]"
    volumes:
      - cache[bold]data:/data
    profiles: [valkey]
volumes:
  cache[bold]data: {}
""",
    )

    listed = runner.invoke(app, ["list", "-d"], env={"COLUMNS": "300"})
    explained = runner.invoke(app, ["explain", "valkey"], env={"COLUMNS": "300"})

    assert "valkey[bold]x" in listed.stdout, listed.stdout
    assert "6379[bold]" in listed.stdout, listed.stdout
    assert "cache[bold]data" in explained.stdout, explained.stdout


def test_registry_text_is_printed_as_written(monkeypatch, tmp_path):
    """Rich reads `[...]` as markup, so a workspace description `[/fast]` ended
    `list` and `explain` in MarkupError, and a role lost `[bold]` and `[red]`."""
    from cli_workspace import REGISTRY

    _fixed_workspace(monkeypatch, tmp_path)
    (tmp_path / ".odctl" / "registry.yml").write_text(
        REGISTRY.replace(
            "Event streaming for the tests.", "Event streaming [/fast] for tests."
        ).replace("A broker with a dashboard.", "Set [bold] or [red]x[/red] options.")
    )

    for args in (["list"], ["explain", "kafka-lite"]):
        result = runner.invoke(app, args, env={"COLUMNS": "200"})
        assert result.exit_code == 0, (args, result.exception)
        assert "Event streaming [/fast] for tests." in result.stdout, args
    explained = runner.invoke(app, ["explain", "kafka-lite"], env={"COLUMNS": "200"})
    assert "Set [bold] or [red]x[/red] options." in explained.stdout


def test_an_error_prints_its_details_as_written(capsys):
    """Docker's stderr can hold `[/data]`, which raised MarkupError in print_error."""
    ui.print_error("Failed to stop compose-[x].yml", details="volume [/data] is in use")

    out = capsys.readouterr().out
    assert "Failed to stop compose-[x].yml" in out
    assert "volume [/data] is in use" in out


def test_the_panel_prints_the_ports_the_json_holds(monkeypatch, tmp_path):
    """The panel split the raw spec, so `${KAFKA_PORT:-19092}` printed as `Host
    -19092}` and `8080`, published on a random host port, as `Host 8080`."""
    from cli_workspace import COMPOSE_KAFKA

    _fixed_workspace(monkeypatch, tmp_path)
    monkeypatch.delenv("KAFKA_PORT", raising=False)
    (tmp_path / ".odctl" / "compose-kafka.yml").write_text(
        COMPOSE_KAFKA.replace(
            '"127.0.0.1:9092:9092"', '"127.0.0.1:${KAFKA_PORT:-19092}:9092"'
        ).replace('"127.0.0.1:8086:8080"', '"8080"')
    )

    explained = runner.invoke(app, ["explain", "kafka-lite"], env={"COLUMNS": "100"})

    assert explained.exit_code == 0
    assert "Host 19092 → Container kafka:9092" in explained.stdout
    assert "kafka-ui:8080" not in explained.stdout


def test_the_panel_lists_a_service_built_from_source(monkeypatch, tmp_path):
    """A service with `build:` and no `image` was left out of the containers as
    soon as another service had an image."""
    from cli_workspace import COMPOSE_KAFKA

    _fixed_workspace(monkeypatch, tmp_path)
    (tmp_path / ".odctl" / "compose-kafka.yml").write_text(
        COMPOSE_KAFKA.replace(
            "  kafka-ui:\n    image: ghcr.io/kafbat/kafka-ui:v1.5.0\n",
            "  kafka-ui:\n    build: ./ui\n",
        )
    )

    explained = runner.invoke(app, ["explain", "kafka-lite"], env={"COLUMNS": "100"})

    assert explained.exit_code == 0
    assert "📦 kafka                  (apache/kafka:4.3.2)" in explained.stdout
    assert "📦 kafka-ui               (built locally)" in explained.stdout
    assert "↳ Service Container" in explained.stdout


def test_a_stopped_service_does_not_make_its_profile_active(monkeypatch, tmp_path):
    """A container counts whatever its state, so `kafka-lite` was active with
    `kafka` exited. An exited one-shot container still counts, as `init-base`
    shows in test_ps_json_has_the_documented_keys."""
    _fixed_workspace(monkeypatch, tmp_path)
    containers = fake_containers()
    for container in containers:
        if container.name == "kafka":
            container.state.status = "exited"
            container.state.exit_code = 0
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.docker.get_managed_containers", lambda plan: containers)

    report = json.loads(runner.invoke(app, ["ps", "--all", "--json"]).stdout)

    assert report["active_profiles"] == ["base"]


def test_an_unreachable_profile_warning_goes_to_stderr_with_json(monkeypatch, capfd):
    """The warning printed through its own console, so under `odctl mcp` it landed in
    the stdout part of the `up` tool, apart from every other warning."""
    from odctl import planner

    monkeypatch.setattr(
        planner,
        "find_unreachable_profiles",
        lambda: [("compose-analytics.yml", "ch-keeper", "fluss")],
    )
    ui.set_json_output(True)
    try:
        planner.warn_unreachable_profiles()
    finally:
        ui.set_json_output(False)

    printed = capfd.readouterr()
    assert printed.out == ""
    assert "ch-keeper" in printed.err
    assert "It will never start." in printed.err


@pytest.mark.parametrize(
    "b_states",
    [
        {"init": ("exited", 0), "db": ("running", 0)},
        {"init": ("running", 0), "db": ("exited", 1)},
    ],
    ids=["one-shot of another file", "running service of another file"],
)
def test_a_service_counts_only_in_its_own_project(monkeypatch, tmp_path, b_states):
    """Services were matched by name across files: a one-shot `init` of one file let
    another file's plain `init` count once it exited, and a running `db` of one file
    counted for another file's stopped `db`."""
    from types import SimpleNamespace

    from odctl import docker, reports

    (tmp_path / "compose-a.yml").write_text(
        "name: a\nservices:\n  init:\n    profiles: [pa]\n"
        "  app:\n    profiles: [pa]\n"
        "    depends_on:\n      init:\n        condition: service_completed_successfully\n"
        "  db:\n    profiles: [pa]\n"
    )
    (tmp_path / "compose-b.yml").write_text(
        "name: b\nservices:\n  init:\n    profiles: [pb]\n  db:\n    profiles: [pb]\n"
        "  cache:\n    profiles: [pb]\n"
    )
    monkeypatch.setattr(docker, "get_compose_path", lambda x: tmp_path / x)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    def container(project, service, status, exit_code=0):
        labels = {
            "com.docker.compose.project": project,
            "com.docker.compose.service": service,
        }
        return SimpleNamespace(
            config=SimpleNamespace(labels=labels),
            state=SimpleNamespace(status=status, exit_code=exit_code),
        )

    containers = [
        container("a", "init", "exited"),
        container("a", "app", "running"),
        container("a", "db", "running"),
        *(container("b", name, *state) for name, state in b_states.items()),
        container("b", "cache", "running"),
    ]
    plan = {"compose-a.yml": ["pa"], "compose-b.yml": ["pb"]}

    assert reports._active_profiles(plan, containers) == ["pa"]
