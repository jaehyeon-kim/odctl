import os
import platform
from typing import List, Tuple

from python_on_whales import DockerClient

from dml.config import get_compose_path


def get_docker_host() -> str:
    """Detects the correct Docker host based on the OS or environment variables."""
    # 1. Priority: Manual environment override
    env_host = os.getenv("DOCKER_HOST")
    if env_host:
        return env_host

    # 2. OS-specific defaults
    system = platform.system()
    if system == "Windows":
        return "npipe:////./pipe/docker_engine"

    # macOS (Darwin) and Linux default
    return "unix:///var/run/docker.sock"


# Global client used for basic checks (like ping)
client = DockerClient(host=get_docker_host())


def is_docker_running() -> bool:
    """Checks if the Docker daemon is reachable."""
    try:
        return client.ping()
    except Exception:
        return False


def get_stack_details(
    compose_filename: str, profiles: List[str]
) -> Tuple[List[str], List[str]]:
    """Resolves services and host port mappings via Docker Compose config."""
    path = get_compose_path(compose_filename)
    if not path.exists():
        return ["File Error"], ["File Error"]

    stack_client = DockerClient(
        host=get_docker_host(),
        compose_files=[str(path)],
        compose_profiles=profiles,
    )

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
    stack_client = DockerClient(host=get_docker_host(), compose_files=[str(path)])
    # python-on-whales handles the output streaming automatically
    stack_client.compose.pull(profiles=profiles)


def launch_stack(compose_filename: str, profiles: List[str]):
    """Starts the stack via docker compose up."""
    path = get_compose_path(compose_filename)
    stack_client = DockerClient(host=get_docker_host(), compose_files=[str(path)])
    # detach=True runs in background, wait=True waits for healthchecks
    stack_client.compose.up(profiles=profiles, detach=True, wait=True)


def stop_stack(
    compose_filename: str, profiles: List[str], remove_volumes: bool = False
):
    """Stops and removes containers and networks for a stack."""
    path = get_compose_path(compose_filename)
    stack_client = DockerClient(host=get_docker_host(), compose_files=[str(path)])
    # volumes=True will remove named volumes defined in the compose file
    stack_client.compose.down(profiles=profiles, volumes=remove_volumes)
