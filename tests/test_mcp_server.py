"""`odctl mcp` serves odctl's commands as tools, and each tool gives what its command gives."""

import json
import subprocess
import sys
from unittest.mock import MagicMock

import anyio
import pytest
from typer.testing import CliRunner

mcp = pytest.importorskip("mcp")

from mcp import Client, StdioServerParameters  # noqa: E402

from cli_workspace import fake_containers, write_workspace  # noqa: E402
from odctl.main import app  # noqa: E402
from odctl.mcp_server import build_server  # noqa: E402

runner = CliRunner()

READ_TOOLS = {"list", "explain", "ps", "info", "logs"}
# The names of the tools and of their parameters stay the same in every 1.x release.
TOOL_PARAMETERS = {
    "list": [],
    "explain": ["profile"],
    "ps": ["profiles"],
    "info": [],
    "logs": ["profiles", "service", "since", "tail", "timestamps", "until"],
    "up": ["profiles", "pull"],
    "down": ["profiles", "volumes"],
}


@pytest.fixture
def fixed_state(monkeypatch, tmp_path):
    """The fixed registry, the fixed containers and a reachable Docker, as the JSON tests use."""
    write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: True)
    monkeypatch.setattr(
        "odctl.docker.get_managed_containers", lambda plan: fake_containers()
    )
    monkeypatch.setattr("odctl.docker.is_docker_running", lambda: True)
    monkeypatch.setattr("odctl.docker.image_is_local", lambda reference: True)
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "1.2.3")


def _call(name, arguments=None, allow_changes=False):
    """Call one tool through an in-process client and return the result."""

    async def run():
        async with Client(build_server(allow_changes)) as client:
            return await client.call_tool(name, arguments or {})

    return anyio.run(run)


def _tools(allow_changes):
    """The tools an in-process client lists, by name."""

    async def run():
        async with Client(build_server(allow_changes)) as client:
            return (await client.list_tools()).tools

    return {tool.name: tool for tool in anyio.run(run)}


def _cli_json(*args):
    """What the command prints with `--json`."""
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0
    return json.loads(result.stdout)


def test_the_read_tools_are_listed_and_the_change_tools_need_the_option():
    read_only = _tools(allow_changes=False)
    with_changes = _tools(allow_changes=True)

    assert set(read_only) == READ_TOOLS
    assert all(tool.annotations.read_only_hint for tool in read_only.values())
    assert with_changes["down"].annotations.destructive_hint is True
    assert with_changes["up"].annotations.destructive_hint is True


def test_tool_and_parameter_names_stay_stable():
    tools = _tools(allow_changes=True)

    assert {
        name: sorted(tool.input_schema.get("properties", {}))
        for name, tool in tools.items()
    } == TOOL_PARAMETERS


@pytest.mark.parametrize(
    "tool, arguments, command, expected_from",
    [
        ("list", {}, ["list"], lambda document: {"result": document}),
        ("explain", {"profile": "kafka-lite"}, ["explain", "kafka-lite"], None),
        ("ps", {}, ["ps", "--all"], None),
        ("ps", {"profiles": ["kafka-lite"]}, ["ps", "kafka-lite"], None),
        ("info", {}, ["info"], None),
    ],
    ids=["list", "explain", "ps-all", "ps-profiles", "info"],
)
def test_the_state_tools_return_the_json_of_the_command(
    fixed_state, tool, arguments, command, expected_from
):
    document = _cli_json(*command)

    result = _call(tool, arguments)

    assert not result.is_error
    expected = expected_from(document) if expected_from else document
    assert result.structured_content == expected


def test_logs_returns_what_the_command_prints(fixed_state, monkeypatch):
    compose = MagicMock()
    compose.compose.logs.return_value = "kafka  | started"
    monkeypatch.setattr("odctl.logs.build_compose_clients", lambda plan: [compose])
    printed = runner.invoke(app, ["logs", "kafka-lite", "-n", "100", "-s", "kafka"])

    result = _call("logs", {"profiles": ["kafka-lite"], "service": "kafka"})

    assert not result.is_error
    assert result.content[0].text == printed.stdout.rstrip()
    assert "kafka  | started" in result.content[0].text
    assert compose.compose.logs.call_args.kwargs["tail"] == "100"
    assert compose.compose.logs.call_args.kwargs["services"] == ["kafka"]


@pytest.mark.parametrize(
    "tool, arguments, message",
    [
        ("explain", {"profile": "nope"}, "Profile 'nope' not found in registry."),
        ("ps", {"profiles": ["nope"]}, "Unknown profiles: nope"),
        ("logs", {"profiles": ["nope"]}, "Unknown profiles: nope"),
    ],
    ids=["explain", "ps", "logs"],
)
def test_an_unknown_profile_returns_the_message_of_the_command(
    fixed_state, tool, arguments, message
):
    result = _call(tool, arguments)

    assert result.is_error
    assert message in result.content[0].text


def test_ps_without_docker_returns_the_message_of_the_command(fixed_state, monkeypatch):
    monkeypatch.setattr("odctl.main.is_docker_running", lambda: False)

    result = _call("ps")

    assert result.is_error
    assert "Docker is not reachable." in result.content[0].text


def test_down_without_a_profile_is_an_error_that_stops_nothing(
    fixed_state, monkeypatch
):
    mock_stop = MagicMock()
    monkeypatch.setattr("odctl.main.stop_stack", mock_stop)

    result = _call("down", {"profiles": []}, allow_changes=True)

    assert result.is_error
    assert "Name at least one profile." in result.content[0].text
    mock_stop.assert_not_called()


def _no_prompt(*args, **kwargs):
    raise AssertionError("a tool must never prompt")


def test_up_and_down_call_the_commands_with_the_arguments_the_cli_passes(
    fixed_state, monkeypatch
):
    monkeypatch.setattr("odctl.main.find_unpublished_images", lambda plan: [])
    monkeypatch.setattr("odctl.main.get_managed_containers", lambda plan: [])
    monkeypatch.setattr("odctl.main.typer.confirm", _no_prompt)
    mocks = {}
    for name in ("launch_stack", "pull_stack_images", "stop_stack"):
        mocks[name] = MagicMock()
        monkeypatch.setattr(f"odctl.main.{name}", mocks[name])

    runner.invoke(app, ["up", "kafka-lite", "--pull"])
    runner.invoke(app, ["down", "kafka-lite", "--volumes"])
    from_cli = {name: mock.call_args_list for name, mock in mocks.items()}
    for mock in mocks.values():
        mock.reset_mock()

    up = _call("up", {"profiles": ["kafka-lite"], "pull": True}, allow_changes=True)
    down = _call("down", {"profiles": ["kafka-lite"], "volumes": True}, True)

    assert from_cli["launch_stack"]
    assert from_cli["stop_stack"]
    assert {name: mock.call_args_list for name, mock in mocks.items()} == from_cli
    assert "All requested profiles successfully started!" in up.content[0].text
    assert "Teardown complete." in down.content[0].text


def test_a_warning_stays_off_the_protocol_stream(tmp_path):
    """`odctl mcp` is started as a client starts it, in a workspace whose TAG differs from
    the CLI version, so the stale-workspace warning is printed. A client does not fail on
    a line that is not a message, so stdout itself must hold nothing before the first
    message. `list` needs no Docker."""
    workspace = write_workspace(tmp_path)
    (workspace / ".env").write_text("TAG=0.0.1\n")
    command = [sys.executable, "-c", "from odctl.main import app; app()", "mcp"]

    closed_at_once = subprocess.run(
        command, cwd=tmp_path, input=b"", capture_output=True, timeout=60
    )
    assert closed_at_once.stdout == b""
    assert b"TAG=0.0.1" in closed_at_once.stderr

    async def run():
        server = StdioServerParameters(
            command=command[0], args=command[1:], cwd=tmp_path
        )
        async with Client(server) as client:
            return await client.call_tool("list", {})

    result = anyio.run(run)

    assert not result.is_error
    assert [p["profile"] for p in result.structured_content["result"]] == [
        "base",
        "kafka-full",
        "kafka-lite",
        "valkey",
    ]
