import os
from typing import List, Tuple

import yaml
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
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Resolves services, host port mappings, images, and volumes via direct YAML parsing."""
    path = get_compose_path(compose_filename)
    if not path.exists():
        return ["File Error"], ["File Error"], ["File Error"], ["File Error"]

    try:
        with open(path, "r") as f:
            compose_dict = yaml.safe_load(f)

        services = []
        ports = []
        images = []
        volumes = []

        # Parse the raw dictionary directly
        for svc_name, svc_data in compose_dict.get("services", {}).items():
            svc_profiles = svc_data.get("profiles", [])

            # Check if this service belongs to the profiles we are querying
            if any(p in profiles for p in svc_profiles):
                services.append(svc_name)

                if "image" in svc_data:
                    images.append(f"{svc_name} -> {svc_data['image']}")

                if "ports" in svc_data:
                    for p in svc_data["ports"]:
                        if isinstance(p, str):
                            ports.append(f"{svc_name}:{p}")
                        elif isinstance(p, dict) and "published" in p:
                            target = p.get("target", p["published"])
                            ports.append(f"{svc_name}:{p['published']}:{target}")

                if "volumes" in svc_data:
                    for v in svc_data["volumes"]:
                        if isinstance(v, str):
                            vol_name = v.split(":")[0]
                            # Only track named volumes, ignore local host bind mounts (./ or /)
                            if not vol_name.startswith((".", "/")):
                                volumes.append(vol_name)
                        elif isinstance(v, dict) and v.get("type") == "volume":
                            volumes.append(v.get("source"))

        return (
            sorted(list(set(services))),
            sorted(list(set(ports))),
            sorted(list(set(images))),
            sorted(list(set(volumes))),
        )
    except Exception as e:
        err = f"Err: {type(e).__name__}"
        return [err], [err], [err], [err]


def pull_stack_images(compose_filename: str, profiles: List[str]):
    """Pulls required images for the stack."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    stack_client.compose.pull()


def launch_stack(compose_filename: str, profiles: List[str]):
    """Starts the stack via docker compose up."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)

    # The 'deps' profile contains an ephemeral container that exits after copying files.
    # Docker Compose's --wait flag fails if it sees a container exit (even with code 0).
    if "deps" in profiles:
        # detach=False blocks until the init container gracefully finishes its job
        stack_client.compose.up(detach=False)
    else:
        # For all other long-running services, we detach and wait for healthchecks
        stack_client.compose.up(detach=True, wait=True)


def stop_stack(
    compose_filename: str, profiles: List[str], remove_volumes: bool = False
):
    """Stops and removes containers and networks for a stack."""
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    # volumes=True will remove named volumes defined in the compose file
    stack_client.compose.down(volumes=remove_volumes)
