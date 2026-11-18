"""`odctl logs`: the log history or live stream of a plan's containers.

A plan can span several compose files, each its own Compose project, so the
logs of each project are fetched with its own client and, when following, each
stream runs in its own thread.
"""

import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from odctl.docker import get_stack_details
from odctl.projects import build_compose_clients

# Serialises the log lines that several follow threads write.
_stdout_lock = threading.Lock()


class UnknownServiceError(ValueError):
    """No compose file of the plan defines the service `logs --service` names."""


class LogsError(Exception):
    """`docker compose logs` failed for one compose file of the plan."""

    def __init__(self, file: str, error: DockerException):
        """
        Record the file and the Docker error.

        Args:
            file (str): The compose file whose logs failed.
            error (DockerException): The error of `docker compose logs`.
        """
        super().__init__(f"Failed to fetch logs for {file}")
        self.file = file
        self.error = error


def _files_with_service(
    execution_plan: Dict[str, List[str]], service: str
) -> Dict[str, List[str]]:
    """The part of the plan whose compose file defines `service`.

    Each file is its own project, and compose refuses a service its file does
    not define, so only the file that holds it is asked for its logs.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
        service (str): The compose service name.

    Returns:
        Dict[str, List[str]]: The entries of `execution_plan` whose file defines `service`.

    Raises:
        UnknownServiceError: If no file of the plan defines `service`, which Compose would
            refuse, so the logs would be empty with no reason given.
    """
    selected: Dict[str, List[str]] = {}
    for file, profiles in execution_plan.items():
        services = get_stack_details(file, profiles).names
        if service in services:
            selected[file] = profiles
    if not selected:
        named = ", ".join(p for profiles in execution_plan.values() for p in profiles)
        raise UnknownServiceError(f"No service '{service}' in the profiles {named}.")
    return selected


def _follow_one(
    file: str,
    compose_client: DockerClient,
    options: Dict[str, Any],
    errors: List[LogsError],
) -> None:
    """Copy one project's log stream to stdout until it ends.

    It runs in its own thread, where a raised error would only reach
    `threading.excepthook`, so a failure is added to `errors` for the main thread.

    Args:
        file (str): The compose file of the client.
        compose_client (DockerClient): The client of one compose file.
        options (Dict[str, Any]): Keyword arguments for `compose.logs`.
        errors (List[LogsError]): Gets the failure of `docker compose logs`, unless
            it is the exit of Ctrl+C.
    """
    try:
        for _, content in compose_client.compose.logs(
            stream=True, follow=True, **options
        ):
            with _stdout_lock:
                # Raw bytes keep Docker Compose's own formatting.
                sys.stdout.buffer.write(content)
                sys.stdout.flush()
    except DockerException as e:
        # Ctrl+C reaches `docker compose logs` too, which then exits with 130;
        # that is the end of the stream, not an error.
        if e.return_code != 130:
            errors.append(LogsError(file, e))


def _follow_all(
    compose_clients: List[Tuple[str, DockerClient]], options: Dict[str, Any]
) -> None:
    """Stream every project's logs at once, one thread per project.

    The threads are daemons, joined with a timeout, so Ctrl+C reaches the main
    thread at once and the process can exit while a stream still blocks. A failed
    stream ends the command at once, while the others still follow, and Ctrl+C
    after a failure still reports it. The other streams' `docker compose logs`
    end when they next write, because their output pipe closes with odctl.

    Args:
        compose_clients (List[Tuple[str, DockerClient]]): Each compose file with its client.
        options (Dict[str, Any]): Keyword arguments for `compose.logs`.

    Raises:
        LogsError: The first stream that failed, as soon as it fails.
    """
    errors: List[LogsError] = []
    threads = [
        threading.Thread(
            target=_follow_one, args=(file, c, options, errors), daemon=True
        )
        for file, c in compose_clients
    ]
    for thread in threads:
        thread.start()
    try:
        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=0.5)
                if errors:
                    raise errors[0]
    except KeyboardInterrupt:
        if errors:
            raise errors[0] from None
        raise
    if errors:
        raise errors[0]


def get_managed_logs(
    execution_plan: Dict[str, List[str]],
    follow: bool = False,
    tail: str = "all",
    timestamps: bool = False,
    since: Optional[str] = None,
    until: Optional[str] = None,
    service: Optional[str] = None,
):
    """
    Fetch or stream logs for the requested execution plan.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
        follow (bool, optional): If True, streams the logs continuously. Defaults to False.
        tail (str, optional): Number of lines to show from the end of the logs. Defaults to "all".
        timestamps (bool, optional): If True, prints timestamps for each log line. Defaults to False.
        since (str, optional): Show logs since a specific timestamp or relative time. Defaults to None.
        until (str, optional): Show logs before a specific timestamp or relative time. Defaults to None.
        service (str, optional): Restrict logs to a specific compose service name. Defaults to None.

    Raises:
        UnknownServiceError: If `service` is set and no compose file of the plan
            defines it.
        LogsError: If `docker compose logs` fails for a compose file.
    """
    options: Dict[str, Any] = {}
    if service:
        execution_plan = _files_with_service(execution_plan, service)
        options["services"] = [service]
    if tail != "all":
        options["tail"] = tail
    if timestamps:
        options["timestamps"] = True
    if since:
        options["since"] = since
    if until:
        options["until"] = until
    compose_clients = list(zip(execution_plan, build_compose_clients(execution_plan)))

    try:
        if follow:
            _follow_all(compose_clients, options)
            return
        for file, compose_client in compose_clients:
            # Fetches the log history as a single string block
            try:
                logs_output = compose_client.compose.logs(**options)
            except DockerException as e:
                raise LogsError(file, e) from e
            if logs_output:
                print(logs_output)
    except KeyboardInterrupt:
        pass  # Handle user pressing Ctrl+C gracefully
