"""Commands on the containers of a plan that already runs: restart and recreate.

`odctl up` starts each compose file as its own Compose project, named by the
file's top-level `name:` (odctl-infra, odctl-kafka and so on). These commands
take a plan that can span several files, so they run one client per file and
reach the same containers `up` created.
"""

from typing import Dict, List

from python_on_whales import DockerClient

from odctl.config import get_compose_path
from odctl.docker import create_client, wait_for_one_shot_containers


def build_compose_clients(execution_plan: Dict[str, List[str]]) -> List[DockerClient]:
    """
    Build one DockerClient per compose file of the plan, in the plan's order.

    `odctl up` runs each compose file as its own project, named by the file's
    top-level `name:` (odctl-infra, odctl-kafka and so on), so a command that acts
    on the same containers must do the same. Passing every file to one client
    merges them into a single project named by the last file, which then tries to
    create containers whose fixed names the other projects already hold
    ("Conflict. The container name "/seaweed" is already in use"), and leaves out
    the containers of the other projects from restart and logs.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[DockerClient]: One client for each file, set to that file's profiles.
    """
    return [
        create_client(compose_files=[str(get_compose_path(file))], profiles=profiles)
        for file, profiles in execution_plan.items()
    ]


def restart_managed_containers(execution_plan: Dict[str, List[str]]):
    """
    Restart containers across all requested profiles.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
    """
    for compose_client in build_compose_clients(execution_plan):
        compose_client.compose.restart()


def recreate_managed_containers(
    execution_plan: Dict[str, List[str]], pull: bool = False
):
    """
    Replace the containers of the requested profiles.

    A restart keeps the container, so an edit to a compose file never reaches it.
    This replaces each one from its current definition instead, which is what
    applies a new memory limit, port, image tag or environment variable. Profiles
    outside the plan are untouched, unlike `up`, which stops what it is not asked
    for. Files are recreated in the plan's order, which puts the infrastructure
    first, as `up` does.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
        pull (bool, optional): Pull images before recreating. Defaults to False.
    """
    for compose_client in build_compose_clients(execution_plan):
        wait_for_one_shot_containers()
        compose_client.compose.up(
            detach=True,
            wait=True,
            force_recreate=True,
            pull="always" if pull else "missing",
        )
    # The wait above passes while a one-shot container is still at work, so the
    # next command could find it running; wait here until it has finished.
    wait_for_one_shot_containers()
