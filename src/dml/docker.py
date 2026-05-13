import os
from typing import List, Tuple

from python_on_whales import DockerClient

from dml.config import get_compose_path


def _create_client(
    compose_files: List[str] = None, profiles: List[str] = None
) -> DockerClient:
    """
    Creates a Docker client that naturally honors the system's Docker context.
    We only inject the host if the user explicitly set DOCKER_HOST.
    """
    kwargs = {}

    if "DOCKER_HOST" in os.environ:
        kwargs["host"] = os.environ["DOCKER_HOST"]

    if compose_files:
        kwargs["compose_files"] = compose_files

    if profiles:
        kwargs["compose_profiles"] = profiles

    return DockerClient(**kwargs)


# Global client used for basic checks
client = _create_client()


def is_docker_running() -> bool:
    """Checks if the Docker daemon is reachable."""
    try:
        # Changed from client.ping() to client.system.info()
        client.system.info()
        return True
    except Exception:
        return False


def get_stack_details(
    compose_filename: str, profiles: List[str]
) -> Tuple[List[str], List[str]]:
    """Resolves services and host port mappings via Docker Compose config."""
    path = get_compose_path(compose_filename)
    if not path.exists():
        return ["File Error"], ["File Error"]

    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)

    try:
        cfg = stack_client.compose.config()
        services = []
        ports = []
        if cfg and cfg.services:
            for name, service in cfg.services.items():
                services.append(name)
                if service.ports:
                    for p in service.ports:
                        if p.published:
                            ports.append(f"{name}:{p.published}")
        return sorted(list(set(services))), sorted(list(set(ports)))
    except Exception as e:
        err = f"Err: {type(e).__name__}"
        return [err], [err]


def pull_stack_images(compose_filename: str, profiles: List[str]):
    """Pulls required images for the stack."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    stack_client.compose.pull()


def launch_stack(compose_filename: str, profiles: List[str]):
    """Starts the stack via docker compose up."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    # detach=True runs in background, wait=True waits for healthchecks
    stack_client.compose.up(detach=True, wait=True)


def stop_stack(
    compose_filename: str, profiles: List[str], remove_volumes: bool = False
):
    """Stops and removes containers and networks for a stack."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    # volumes=True will remove named volumes defined in the compose file
    stack_client.compose.down(volumes=remove_volumes)
