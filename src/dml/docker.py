from typing import List
from python_on_whales import DockerClient
from dml.config import get_compose_path

# Initialize with the explicit Unix socket for Linux stability
client = DockerClient(host="unix:///var/run/docker.sock")


def is_docker_running() -> bool:
    try:
        return client.ping()
    except Exception:
        return False


def get_stack_ports(compose_filename: str, profiles: List[str]) -> List[str]:
    """Resolves host port mappings via Docker Compose config."""
    path = get_compose_path(compose_filename)
    if not path.exists():
        return ["File Error"]

    stack_client = DockerClient(
        host="unix:///var/run/docker.sock", compose_files=[str(path)]
    )

    try:
        cfg = stack_client.compose.config(profiles=profiles)
        ports = []
        if cfg and cfg.services:
            for name, service in cfg.services.items():
                if service.ports:
                    for p in service.ports:
                        if p.published:
                            ports.append(f"{name}:{p.published}")
        return sorted(list(set(ports)))
    except Exception as e:
        return [f"Err: {type(e).__name__}"]
