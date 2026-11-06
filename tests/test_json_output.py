import json

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


@pytest.mark.parametrize(
    "compose, marker",
    [(None, "File Error"), ("services: [\n", "Err: ")],
    ids=["missing", "unparsable"],
)
def test_unreadable_compose_file_in_the_tables_and_in_json(
    monkeypatch, tmp_path, compose, marker
):
    """The tables show the error marker and exit 0; --json fails on stderr."""
    _fixed_workspace(monkeypatch, tmp_path)
    cache = tmp_path / ".odctl" / "compose-cache.yml"
    if compose is None:
        cache.unlink()
    else:
        cache.write_text(compose)

    for args in (["list", "-d"], ["explain", "valkey"]):
        table = runner.invoke(app, args, env={"COLUMNS": "100"})
        assert table.exit_code == 0, args
        assert table.exception is None, args
        assert marker in table.stdout, args

    for args in (["list", "--json"], ["explain", "valkey", "--json"]):
        failed = runner.invoke(app, args)
        assert failed.exit_code == 1, args
        assert failed.stdout == "", args
        assert "Cannot read compose-cache.yml" in failed.stderr, args
        assert marker in failed.stderr, args


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
    assert "Host -6379} → Container valkey:6379" in explained
    assert "Container valkey:6379" in explained
    assert "Container valkey:7000-7001" in explained
    assert "Container valkey:6380/tcp" in explained

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


def test_unknown_dependency_fails_only_what_needs_it(monkeypatch, tmp_path):
    """The list tables do not work out `starts`; the JSON and the panel name the dependency."""
    _fixed_workspace(monkeypatch, tmp_path)
    registry = tmp_path / ".odctl" / "registry.yml"
    registry.write_text(
        registry.read_text().replace("valkey: [kafka-lite]", "valkey: [kafka-lit]")
    )

    assert runner.invoke(app, ["list"]).exit_code == 0
    assert runner.invoke(app, ["list", "-d"]).exit_code == 0

    for args in (["list", "--json"], ["explain", "valkey", "--json"]):
        failed = runner.invoke(app, args)
        assert failed.exit_code == 1, args
        assert failed.stdout == "", args
        assert "'valkey'" in failed.stderr, args
        assert "'kafka-lit'" in failed.stderr, args

    panel = runner.invoke(app, ["explain", "valkey"])
    assert panel.exit_code == 1
    assert "'kafka-lit'" in panel.stdout


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


def test_info_json_without_a_registry_prints_an_error(monkeypatch, tmp_path):
    """A workspace with no registry.yml gives a message on stderr, not a traceback."""
    (tmp_path / ".odctl").mkdir()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["info", "--json"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Registry file not found" in result.stderr
    assert not isinstance(result.exception, FileNotFoundError)
