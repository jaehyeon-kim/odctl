import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from python_on_whales import DockerClient

from odctl.config import get_active_dir, get_compose_path


def _create_client(
    compose_files: List[str] | None = None, profiles: List[str] | None = None
) -> DockerClient:
    """
    Create a Docker client that naturally honors the system's Docker context.

    Args:
        compose_files (List[str], optional): A list of paths to docker-compose files. Defaults to None.
        profiles (List[str], optional): A list of compose profiles to activate. Defaults to None.

    Returns:
        DockerClient: An initialized python-on-whales Docker client.
    """
    kwargs: Dict[str, Any] = {}

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
    """
    Check if the Docker daemon is reachable.

    Returns:
        bool: True if the Docker engine responds to system info requests, False otherwise.
    """
    try:
        # Changed from client.ping() to client.system.info()
        client.system.info()
        return True
    except Exception:
        return False


def get_stack_details(
    compose_filename: str, profiles: List[str]
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Resolve services, host port mappings, images, and volumes via direct YAML parsing.

    Args:
        compose_filename (str): The name of the compose file to parse.
        profiles (List[str]): The active profiles to filter services by.

    Returns:
        Tuple[List[str], List[str], List[str], List[str]]: A tuple containing four sorted lists:
            services, exposed host ports, container images, and named volumes.
            Returns lists containing "File Error" if the file cannot be parsed.
    """
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
                            source = v.get("source")
                            if isinstance(source, str):
                                volumes.append(source)

        # Drop volumes the file declares as external. Compose never removes
        # those, so mounting one is not a reason to tear a profile down. Counting
        # them made `odctl down --all --volumes` select `catalog` purely because
        # it mounts the shared dependency volume, even when nothing of it ran.
        declared = compose_dict.get("volumes") or {}
        external = {
            name
            for name, spec in declared.items()
            if isinstance(spec, dict) and spec.get("external")
        }
        volumes = [v for v in volumes if v not in external]

        return (
            sorted(list(set(services))),
            sorted(list(set(ports))),
            sorted(list(set(images))),
            sorted(list(set(volumes))),
        )
    except Exception as e:
        err = f"Err: {type(e).__name__}"
        return [err], [err], [err], [err]


# Images this project builds and publishes itself. They carry the CLI version as
# their tag, so a version whose build has not finished has no image to pull.
# Every other image in the compose files is a third-party one pinned to an exact
# upstream version, and those are never checked here.
ODCTL_IMAGE_PREFIX = "ghcr.io/jaehyeon-kim/odctl/"

# Compose interpolation, limited to the forms the compose files use:
# ${VAR}, ${VAR:-default} and ${VAR-default}.
_VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?-)([^}]*))?\}")

# Registry replies that mean the tag is genuinely absent. Anything else, a DNS
# failure or a refused connection for instance, leaves the answer unknown, and
# an unknown answer must not stop a launch.
_ABSENT_MARKERS = ("manifest unknown", "no such manifest", "not found")


def _read_env_file(path: Path) -> Dict[str, str]:
    """
    Parse a compose `.env` file into a plain dictionary.

    Args:
        path (Path): Path to the `.env` file. A missing file yields an empty mapping.

    Returns:
        Dict[str, str]: The declared variables, with surrounding quotes removed.
    """
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _interpolation_env() -> Dict[str, str]:
    """
    Build the variable mapping compose uses to interpolate the compose files.

    Compose reads `.env` from the project directory, which is the directory
    holding the compose file, and lets the shell environment override it.

    Returns:
        Dict[str, str]: Variables from the active directory's `.env`, overridden
        by the current process environment.
    """
    env = _read_env_file(get_active_dir() / ".env")
    env.update(os.environ)
    return env


def _expand(value: str, env: Dict[str, str]) -> str:
    """
    Substitute compose variables in a string.

    Args:
        value (str): A raw value from a compose file, such as an image reference.
        env (Dict[str, str]): The variables to substitute.

    Returns:
        str: The value with every recognised variable reference replaced.
    """

    def replace(match: re.Match) -> str:
        name, operator, default = match.group(1), match.group(2), match.group(3)
        current = env.get(name)
        if operator is None:
            return current or ""
        if operator == ":-":
            return current if current else default
        return default if current is None else current

    return _VARIABLE_PATTERN.sub(replace, value)


def resolve_image_tag() -> str:
    """
    Resolve the tag the compose files will put on the images odctl builds.

    Returns:
        str: The value of TAG as compose resolves it, or 'latest' when unset.
    """
    return _expand("${TAG:-latest}", _interpolation_env())


def get_versioned_images(execution_plan: Dict[str, List[str]]) -> List[str]:
    """
    List the version-coupled image references an execution plan needs.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[str]: Sorted, deduplicated references to images built by this
        project, with their variables already substituted.
    """
    env = _interpolation_env()
    references = set()

    for file, profiles in execution_plan.items():
        _, _, images, _ = get_stack_details(file, profiles)
        for entry in images:
            _, _, raw = entry.partition(" -> ")
            reference = _expand(raw, env)
            if reference.startswith(ODCTL_IMAGE_PREFIX):
                references.add(reference)

    return sorted(references)


def _image_is_local(reference: str) -> bool:
    """
    Report whether an image is already on the Docker host.

    Args:
        reference (str): A full image reference.

    Returns:
        bool: True when the local daemon holds the image.
    """
    try:
        return bool(client.image.exists(reference))
    except Exception:
        return False


def _registry_has_image(reference: str) -> Optional[bool]:
    """
    Ask the registry whether an image tag is published.

    Args:
        reference (str): A full image reference.

    Returns:
        Optional[bool]: True when the registry serves a manifest for it, False
        when the registry says the tag is absent, and None when the question
        could not be answered, which is what an offline machine returns.
    """
    try:
        client.manifest.inspect(reference)
        return True
    except Exception as exc:
        text = f"{getattr(exc, 'stderr', '') or ''} {exc}".lower()
        if any(marker in text for marker in _ABSENT_MARKERS):
            return False
        return None


def find_unpublished_images(execution_plan: Dict[str, List[str]]) -> List[str]:
    """
    Find images an execution plan needs that neither Docker nor the registry has.

    An image already on the host is accepted without a registry call, so a
    machine with no network can still start a stack it has pulled before. A
    registry that cannot be reached leaves the answer unknown, and an unknown
    answer is treated as present so the launch proceeds and Docker reports
    whatever it finds.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[str]: References the registry reported as absent, in sorted order.
    """
    candidates = [
        reference
        for reference in get_versioned_images(execution_plan)
        if not _image_is_local(reference)
    ]
    if not candidates:
        return []

    # Each registry call is a network round trip of a second or more, so ask
    # about every image at once rather than one after another.
    with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
        answers = list(pool.map(_registry_has_image, candidates))

    return [
        reference for reference, answer in zip(candidates, answers) if answer is False
    ]


def pull_stack_images(compose_filename: str, profiles: List[str]):
    """
    Pull required images for a specific stack.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles indicating which services to pull.
    """
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    stack_client.compose.pull()


def launch_stack(compose_filename: str, profiles: List[str]):
    """
    Start the stack via docker compose up.

    If the 'deps' profile is active, this blocks until the ephemeral init container
    finishes. Otherwise, it detaches and waits for healthchecks.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to launch.
    """
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
    """
    Stop and remove containers and networks for a stack.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to stop.
        remove_volumes (bool, optional): If True, destroys named volumes associated
                                         with the stack. Defaults to False.
    """
    path = get_compose_path(compose_filename)
    stack_client = _create_client(compose_files=[str(path)], profiles=profiles)
    # volumes=True will remove named volumes defined in the compose file.
    # remove_orphans catches containers whose service no longer exists in the
    # compose file, which teardown would otherwise leave running forever: an
    # upgrade that drops or renames a service (ch-init-lite in 0.2.0, the
    # flink1-* services in 0.3.0) leaves the old container holding its name.
    stack_client.compose.down(volumes=remove_volumes, remove_orphans=True)


def get_managed_containers(execution_plan: Dict[str, List[str]]) -> List[Any]:
    """
    Fetch Docker containers matching the requested execution plan.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[Any]: A list of python-on-whales Container objects managed by the ODCTL stack.
    """
    target_services = set()
    for file, profs in execution_plan.items():
        # Re-using your existing parser to know exactly which services to look for
        services, _, _, _ = get_stack_details(file, profs)
        target_services.update(services)

    all_containers = client.container.list(all=True)
    managed_containers = []

    for c in all_containers:
        # Safely access labels via the Container's Config block
        labels = c.config.labels if c.config and c.config.labels else {}

        project = labels.get("com.docker.compose.project", "")
        service = labels.get("com.docker.compose.service", "")

        # Strictly enforce that the container belongs to a ODCTL stack AND the requested profile
        if project.startswith("odctl-") and service in target_services:
            managed_containers.append(c)

    return managed_containers


def _build_compose_client(execution_plan: Dict[str, List[str]]) -> DockerClient:
    """
    Build a unified DockerClient for multiple compose files and profiles.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        DockerClient: A client configured to target all specified files and profiles simultaneously.
    """
    files = [str(get_compose_path(f)) for f in execution_plan.keys()]
    # Flatten the lists of profiles and deduplicate them
    profiles = list(set(p for profs in execution_plan.values() for p in profs))

    # Initialize a single client capable of cross-file execution
    return _create_client(compose_files=files, profiles=profiles)


def restart_managed_containers(execution_plan: Dict[str, List[str]]):
    """
    Restart containers across all requested profiles.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
    """
    compose_client = _build_compose_client(execution_plan)
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
    for.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.
        pull (bool, optional): Pull images before recreating. Defaults to False.
    """
    compose_client = _build_compose_client(execution_plan)
    compose_client.compose.up(
        detach=True,
        wait=True,
        force_recreate=True,
        pull="always" if pull else "missing",
    )


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
    compose_client = _build_compose_client(execution_plan)

    kwargs: Dict[str, Any] = {}
    if service:
        # Compose expects a list of services to filter by
        kwargs["services"] = [service]
    if tail != "all":
        kwargs["tail"] = tail
    if timestamps:
        kwargs["timestamps"] = True
    if since:
        kwargs["since"] = since
    if until:
        kwargs["until"] = until

    try:
        if follow:
            # stream=True yields (source, bytes) tuples in real-time
            for source, content in compose_client.compose.logs(
                stream=True, follow=True, **kwargs
            ):
                # Write raw bytes to preserve Docker Compose's native formatting
                sys.stdout.buffer.write(content)
                sys.stdout.flush()
        else:
            # Fetches the log history as a single string block
            logs_output = compose_client.compose.logs(**kwargs)
            if logs_output:
                print(logs_output)
    except KeyboardInterrupt:
        pass  # Handle user pressing Ctrl+C gracefully
