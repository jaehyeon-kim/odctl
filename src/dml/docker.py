from typing import List, Tuple
from python_on_whales import DockerClient
from dml.config import get_compose_path

# Initialize with the explicit Unix socket for Linux stability
client = DockerClient(host="unix:///var/run/docker.sock")


def is_docker_running() -> bool:
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
        host="unix:///var/run/docker.sock",
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
    stack_client = DockerClient(
        host="unix:///var/run/docker.sock", compose_files=[str(path)]
    )
    # python-on-whales handles the output streaming automatically!
    stack_client.compose.pull(profiles=profiles)


def launch_stack(compose_filename: str, profiles: List[str]):
    """Starts the stack via docker compose up."""
    path = get_compose_path(compose_filename)
    stack_client = DockerClient(
        host="unix:///var/run/docker.sock", compose_files=[str(path)]
    )
    # detach=True runs it in the background, wait=True waits for healthchecks
    stack_client.compose.up(profiles=profiles, detach=True, wait=True)
