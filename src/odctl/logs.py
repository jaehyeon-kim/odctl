"""`odctl logs`: the log history or live stream of a plan's containers.

A plan can span several compose files, each its own Compose project, so the
logs of each project are fetched with its own client and, when following, each
stream runs in its own thread.
"""

import sys
import threading
from typing import Any, Dict, List, Optional

from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from odctl.docker import get_stack_details
from odctl.projects import build_compose_clients

# Serialises the log lines that several follow threads write.
_stdout_lock = threading.Lock()


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
    """
    selected: Dict[str, List[str]] = {}
    for file, profiles in execution_plan.items():
        services = get_stack_details(file, profiles)[0]
        if service in services:
            selected[file] = profiles
    return selected


def _follow_one(compose_client: DockerClient, options: Dict[str, Any]) -> None:
    """Copy one project's log stream to stdout until it ends.

    Args:
        compose_client (DockerClient): The client of one compose file.
        options (Dict[str, Any]): Keyword arguments for `compose.logs`.

    Raises:
        DockerException: When `docker compose logs` fails for a reason other than Ctrl+C.
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
            raise


def _follow_all(compose_clients: List[DockerClient], options: Dict[str, Any]) -> None:
    """Stream every project's logs at once, one thread per project.

    The threads are daemons, joined with a timeout, so Ctrl+C reaches the main
    thread at once and the process can exit while a stream still blocks.

    Args:
        compose_clients (List[DockerClient]): One client per compose file.
        options (Dict[str, Any]): Keyword arguments for `compose.logs`.
    """
    threads = [
        threading.Thread(target=_follow_one, args=(c, options), daemon=True)
        for c in compose_clients
    ]
    for thread in threads:
        thread.start()
    while any(thread.is_alive() for thread in threads):
        for thread in threads:
            thread.join(timeout=0.5)


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
    compose_clients = build_compose_clients(execution_plan)

    try:
        if follow:
            _follow_all(compose_clients, options)
            return
        for compose_client in compose_clients:
            # Fetches the log history as a single string block
            logs_output = compose_client.compose.logs(**options)
            if logs_output:
                print(logs_output)
    except KeyboardInterrupt:
        pass  # Handle user pressing Ctrl+C gracefully
