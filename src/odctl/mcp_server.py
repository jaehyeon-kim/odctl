"""The MCP server of `odctl mcp`: odctl's commands as tools for an AI agent.

Each tool calls the command function of the same name in `odctl.main`, so a tool
never repeats a command's logic. The tools that read state return the models that
`--json` prints.
"""

import contextlib
import io
import threading
from typing import Callable, List, Optional, Tuple

import click
import typer
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import TypeAdapter

from odctl import main
from odctl.models import Info, ProfileDetails, ProfileInfo, PsReport

# One tool runs at a time. Two `up` calls must not start compose at once, and the
# redirect of stdout and stderr in `_run` belongs to one call.
_lock = threading.Lock()

_READ_ONLY = ToolAnnotations(read_only_hint=True)


def _run(command: Callable[..., None], **options) -> Tuple[str, str]:
    """
    Run a command function of `odctl.main` and capture what it prints.

    The commands print with Rich and Click, which look up `sys.stdout` and
    `sys.stderr` when they write, so redirecting both catches every line. Without the
    capture, the lines would reach the protocol stream.

    Args:
        command (Callable[..., None]): The command function to call.
        **options: Every parameter of the command, by name. The command is called as a
            plain function, so Typer does not fill in defaults.

    Returns:
        Tuple[str, str]: What the command wrote to stdout and to stderr.

    Raises:
        ToolError: With the command's output as the message, when the command exits
            with a code other than 0 or is aborted.
    """
    out, err = io.StringIO(), io.StringIO()
    failed = False
    with _lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            command(**options)
        except typer.Exit as exit_:
            failed = bool(exit_.exit_code)
        except click.exceptions.Abort:
            failed = True
    if failed:
        raise ToolError(_text(out.getvalue(), err.getvalue()) or "The command failed.")
    return out.getvalue(), err.getvalue()


def _text(stdout: str, stderr: str) -> str:
    """
    Join what a command printed, stderr first, then stdout.

    `odctl mcp` sends warnings and messages to stderr, as `--json` does, so most of
    what `up` and `down` print is in stderr.

    Args:
        stdout (str): What the command wrote to stdout.
        stderr (str): What the command wrote to stderr.

    Returns:
        str: Both texts joined, without trailing blank lines.
    """
    return (stderr + stdout).rstrip()


def build_server(allow_changes: bool) -> MCPServer:
    """
    Build the MCP server with odctl's tools.

    Args:
        allow_changes (bool): Also serve `up` and `down`, which start and stop profiles.

    Returns:
        MCPServer: The server. `run()` serves it on stdio.
    """
    server = MCPServer("odctl")

    @server.tool(
        name="list",
        description="List every profile with its services and ports, as `odctl list --json` does.",
        annotations=_READ_ONLY,
    )
    def list_profiles() -> List[ProfileInfo]:
        """
        List every profile.

        Returns:
            List[ProfileInfo]: The profiles, sorted by name.

        Raises:
            ToolError: With the command's message when it fails.
        """
        stdout, _ = _run(main.list_profiles, details=False, json_output=True)
        return TypeAdapter(List[ProfileInfo]).validate_json(stdout)

    @server.tool(
        description="Describe one profile: its services, images, ports, volumes and usage, as `odctl explain --json` does.",
        annotations=_READ_ONLY,
    )
    def explain(profile: str) -> ProfileDetails:
        """
        Describe one profile.

        Args:
            profile (str): The profile to describe.

        Returns:
            ProfileDetails: The details of the profile.

        Raises:
            ToolError: With the command's message when the profile is unknown.
        """
        stdout, _ = _run(main.explain, profile=profile, json_output=True)
        return ProfileDetails.model_validate_json(stdout)

    @server.tool(
        description="Show the containers odctl manages and the active profiles, as `odctl ps --json` does. Without profiles it shows every container.",
        annotations=_READ_ONLY,
    )
    def ps(profiles: Optional[List[str]] = None) -> PsReport:
        """
        Show the containers of some profiles, or of all.

        Args:
            profiles (Optional[List[str]]): The profiles whose containers to show; all
                containers when empty.

        Returns:
            PsReport: The active profiles and the containers.

        Raises:
            ToolError: With the command's message when Docker is not reachable or a
                profile is unknown.
        """
        stdout, _ = _run(main.ps, profiles=profiles, all=not profiles, json_output=True)
        return PsReport.model_validate_json(stdout)

    @server.tool(
        description="Show the odctl version, the image tag, the workspace, whether Docker is reachable and odctl's images, as `odctl info --json` does.",
        annotations=_READ_ONLY,
    )
    def info() -> Info:
        """
        Show the odctl version, the workspace and whether Docker is reachable.

        Returns:
            Info: The report. With Docker not reachable it has `reachable: false`.

        Raises:
            ToolError: With the command's message when the workspace has no registry.
        """
        stdout, _ = _run(main.info, json_output=True)
        return Info.model_validate_json(stdout)

    @server.tool(
        description="Fetch the logs of the containers of some profiles, as `odctl logs` prints them, the last 100 lines of each by default.",
        annotations=_READ_ONLY,
    )
    def logs(
        profiles: List[str],
        service: Optional[str] = None,
        tail: int = 100,
        timestamps: bool = False,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> str:
        """
        Fetch the logs of some profiles.

        The default `tail` is 100 lines, not all of them as in the CLI, so one call
        cannot fill an agent's context with a long log. `--follow` has no tool, because
        it never returns.

        Args:
            profiles (List[str]): The profiles whose logs to show.
            service (Optional[str]): Show only this compose service.
            tail (int): How many lines to show from the end of each log.
            timestamps (bool): Show a timestamp on each line.
            since (Optional[str]): Show lines after this time, absolute or relative such as `42m`.
            until (Optional[str]): Show lines before this time, absolute or relative.

        Returns:
            str: The log lines, with any message on stderr first.

        Raises:
            ToolError: With the command's message when Docker is not reachable or a
                profile is unknown.
        """
        stdout, stderr = _run(
            main.logs,
            profiles=profiles,
            service=service,
            follow=False,
            tail=str(tail),
            timestamps=timestamps,
            since=since,
            until=until,
        )
        return _text(stdout, stderr)

    if allow_changes:
        # `up` recreates a container whose definition changed, which loses the data
        # kept inside it (How It Works, Where Data Lives), so it is marked destructive.
        @server.tool(
            description="Start profiles and their dependencies, as `odctl up` does.",
            annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True),
        )
        def up(profiles: List[str], pull: bool = False) -> str:
            """
            Start profiles.

            Args:
                profiles (List[str]): The profiles to start; their dependencies start first.
                pull (bool): Pull the images again before starting.

            Returns:
                str: What `odctl up` prints.

            Raises:
                ToolError: With the command's message when it fails.
            """
            stdout, stderr = _run(main.up, profiles=profiles, dry_run=False, pull=pull)
            return _text(stdout, stderr)

        # The CLI asks before it removes every profile's data (`--all --volumes`),
        # and the server cannot ask. So `down` takes named profiles only, and with
        # `volumes` it refuses names that cover all that `--all --volumes` removes.
        # The destructive hint lets a client ask its user before the call.
        @server.tool(
            description="Stop the named profiles. With `volumes`, also remove their volumes, and the shared jar volume `odctl-shared-deps` once no other profile has a container, as `odctl down --volumes` does.",
            annotations=ToolAnnotations(destructive_hint=True),
        )
        def down(profiles: List[str], volumes: bool = False) -> str:
            """
            Stop profiles.

            Args:
                profiles (List[str]): The profiles to stop.
                volumes (bool): Also remove the volumes of the stopped services.

            Returns:
                str: What `odctl down` prints.

            Raises:
                ToolError: When no profile is named, when `volumes` is set and the
                    profiles cover every profile `odctl down --all --volumes` would
                    stop, or with the command's message when it fails.
            """
            if not profiles:
                raise ToolError("Name at least one profile.")

            def teardown() -> None:
                """Stop the profiles, unless the call would remove every profile's data."""
                if (
                    volumes
                    and main.is_docker_running()
                    and main.removes_everything(profiles)
                ):
                    raise ToolError(
                        "These profiles cover every profile with data, so this call would "
                        "remove all of it. Run `odctl down --all --volumes` in a terminal, "
                        "which asks first, or name fewer profiles."
                    )
                main.down(
                    profiles=profiles,
                    all=False,
                    volumes=volumes,
                    dry_run=False,
                    yes=False,
                )

            stdout, stderr = _run(teardown)
            return _text(stdout, stderr)

    return server
