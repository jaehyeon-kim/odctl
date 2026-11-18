import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set, Tuple

from python_on_whales import DockerClient

from odctl.config import (
    UnreadableFileError,
    expand,
    get_active_dir,
    get_compose_path,
    read_env_file,
    read_yaml,
)


def create_client(
    compose_file: str | None = None, profiles: List[str] | None = None
) -> DockerClient:
    """
    Create a Docker client that naturally honors the system's Docker context.

    A client for a compose file runs it as the project `get_project_name` names, so
    a COMPOSE_PROJECT_NAME in the shell or in `.env` cannot merge every file into one
    project: `--project-name` takes precedence over it (Docker docs, "Specify a
    project name").

    Args:
        compose_file (str, optional): The name of the compose file, such as
            'compose-kafka.yml'. Defaults to None, for a client with no project.
        profiles (List[str], optional): A list of compose profiles to activate. Defaults to None.

    Returns:
        DockerClient: An initialized python-on-whales Docker client.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    kwargs: Dict[str, Any] = {}

    if "DOCKER_HOST" in os.environ:
        kwargs["host"] = os.environ["DOCKER_HOST"]

    if compose_file:
        kwargs["compose_files"] = [str(get_compose_path(compose_file))]
        kwargs["compose_project_name"] = get_project_name(compose_file)

    if profiles:
        kwargs["compose_profiles"] = profiles

    return DockerClient(**kwargs)


# Global client used for basic checks
client = create_client()


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


def read_compose(compose_filename: str) -> Dict[str, Any]:
    """
    Read a compose file of the active directory.

    Args:
        compose_filename (str): The name of the compose file, such as 'compose-kafka.yml'.

    Returns:
        Dict[str, Any]: The file's content. Its `services` entry, when present, maps
        each service name to a mapping.

    Raises:
        UnreadableFileError: As `Cannot read <file>: <reason>`, when the file is missing, is not
            valid YAML, or its top level, its services or one of them is not a mapping.
    """
    compose = read_yaml(get_compose_path(compose_filename), compose_filename)
    if not isinstance(compose, dict):
        raise UnreadableFileError(
            f"Cannot read {compose_filename}: its top level is not a mapping."
        )
    services = compose.get("services")
    if services is None:
        services = {}
    if not isinstance(services, dict):
        raise UnreadableFileError(
            f"Cannot read {compose_filename}: its services are not a mapping."
        )
    for name, service in services.items():
        if not isinstance(service, dict):
            raise UnreadableFileError(
                f"Cannot read {compose_filename}: the service '{name}' is not a mapping."
            )
    return compose


def get_project_name(compose_filename: str) -> str:
    """
    Name the Compose project a compose file runs as, as Compose names it.

    That is the file's top-level `name:`, interpolated, or without one the name of
    the folder that holds the file. Compose then lower-cases it, keeps only a-z,
    0-9, `_` and `-`, and trims `_` and `-` from the start (compose-go
    loader/loader.go, `projectName` and `NormalizeProjectName`).

    Args:
        compose_filename (str): The name of the compose file.

    Returns:
        str: The project name.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose = read_compose(compose_filename)
    name = expand(str(compose.get("name") or ""), interpolation_env())
    name = name or get_compose_path(compose_filename).parent.name
    return re.sub(r"[^a-z0-9_-]", "", name.lower()).lstrip("_-")


def get_stack_details(
    compose_filename: str, profiles: List[str]
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Resolve services, host port mappings, images, and volumes via direct YAML parsing.

    A service with no `profiles` belongs to every profile of its file, because
    Compose starts it whatever profiles are active.

    Args:
        compose_filename (str): The name of the compose file to parse.
        profiles (List[str]): The active profiles to filter services by.

    Returns:
        Tuple[List[str], List[str], List[str], List[str]]: A tuple containing four sorted lists:
            services, exposed host ports, container images, and named volumes.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose_dict = read_compose(compose_filename)
    env = interpolation_env(compose_filename)

    services = []
    ports = []
    images = []
    volumes = []

    # Parse the raw dictionary directly
    for svc_name, svc_data in (compose_dict.get("services") or {}).items():
        svc_profiles = svc_data.get("profiles")

        # Check if this service belongs to the profiles we are querying
        if not svc_profiles or any(p in profiles for p in svc_profiles):
            services.append(svc_name)

            if "image" in svc_data:
                # Shown as it will run: `${TAG:-latest}` resolves the way compose
                # resolves it, which is the CLI version without a workspace.
                image = expand(svc_data["image"], env)
                images.append(f"{svc_name} -> {image}")

            if "ports" in svc_data:
                for p in svc_data["ports"]:
                    if isinstance(p, str):
                        ports.append(f"{svc_name}:{p}")
                    elif isinstance(p, dict) and "published" in p:
                        target = p.get("target", p["published"])
                        protocol = f"/{p['protocol']}" if p.get("protocol") else ""
                        ports.append(f"{svc_name}:{p['published']}:{target}{protocol}")

            if "volumes" in svc_data:
                for v in svc_data["volumes"]:
                    if isinstance(v, str):
                        # Compose interpolates the entry before it splits it, so
                        # `${PG_VOLUME:-pgdata}:/data` mounts the volume `pgdata`.
                        vol_name = expand(v, env).split(":")[0]
                        # Only track named volumes, ignore local host bind mounts (./, / or ~)
                        if not vol_name.startswith((".", "/", "~")):
                            volumes.append(vol_name)
                    elif isinstance(v, dict) and v.get("type") == "volume":
                        source = v.get("source")
                        source = expand(source, env) if isinstance(source, str) else ""
                        if source:
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


# Images this project builds and publishes itself. They carry the CLI version as
# their tag, so a version whose build has not finished has no image to pull.
# Every other image in the compose files is a third-party one pinned to an exact
# upstream version, and those are never checked here.
ODCTL_IMAGE_PREFIX = "ghcr.io/jaehyeon-kim/odctl/"

# Registry replies that mean the tag is genuinely absent. Anything else, a DNS
# failure, a refused connection or a missing credential helper for instance,
# leaves the answer unknown, and an unknown answer must not stop a launch.
_ABSENT_MARKERS = ("manifest unknown", "no such manifest")


def interpolation_env(compose_filename: Optional[str] = None) -> Dict[str, str]:
    """
    Build the variable mapping compose uses to interpolate the compose files.

    Compose reads `.env` from the project directory, which is the directory
    holding the compose file, and lets the shell environment override it. For
    the values of a file, it also sets `COMPOSE_PROJECT_NAME` to the project the
    file runs as, over any value in the shell (compose-go loader/loader.go,
    `projectName`).

    Args:
        compose_filename (str, optional): The compose file whose values are
            expanded. Defaults to None, for a value that belongs to no file.

    Returns:
        Dict[str, str]: Variables from the active directory's `.env`, overridden
        by the current process environment.

    Raises:
        UnreadableFileError: If the compose file cannot be read.
    """
    env = read_env_file(get_active_dir() / ".env")
    env.update(os.environ)
    if compose_filename:
        env["COMPOSE_PROJECT_NAME"] = get_project_name(compose_filename)
    return env


def resolve_image_tag() -> str:
    """
    Resolve the tag the compose files will put on the images odctl builds.

    Returns:
        str: The value of TAG as compose resolves it, or 'latest' when unset.
    """
    return expand("${TAG:-latest}", interpolation_env())


def get_versioned_images(execution_plan: Dict[str, List[str]]) -> List[str]:
    """
    List the version-coupled image references an execution plan needs.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[str]: Sorted, deduplicated references to images built by this
        project, with their variables already substituted.
    """
    references = set()

    for file, profiles in execution_plan.items():
        env = interpolation_env(file)
        _, _, images, _ = get_stack_details(file, profiles)
        for entry in images:
            _, _, raw = entry.partition(" -> ")
            reference = expand(raw, env)
            if reference.startswith(ODCTL_IMAGE_PREFIX):
                references.add(reference)

    return sorted(references)


def image_is_local(reference: str) -> bool:
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
        if not image_is_local(reference)
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
    stack_client = create_client(compose_filename, profiles)
    stack_client.compose.pull()


# Containers that do one job and exit, such as creating the SeaweedFS buckets.
# `docker compose up --wait` fails when a container it finds running exits during
# the wait, even with code 0. `recreate storage` returns while seaweed-init is
# still creating buckets, so an `up` straight after it failed until it finished.
_ONE_SHOT_CONTAINERS = ("seaweed-init",)


def wait_for_one_shot_containers():
    """Block until any one-shot container that is still running has exited."""
    for name in _ONE_SHOT_CONTAINERS:
        if (
            client.container.exists(name)
            and client.container.inspect(name).state.running
        ):
            client.container.wait(name)


def check_exit_codes(stack_client: DockerClient) -> None:
    """
    Fail when a container of an attached `compose up` exited with a code other than 0.

    Attached, Compose returns 0 whatever code a container exits with, unless it is
    told to abort on an exit (docker/compose v5.8.0 pkg/compose/up.go: the exit code
    is set only by the listeners of `--abort-on-container-exit`,
    `--abort-on-container-failure` and `--exit-code-from`). Those flags stop every
    other container of the file when the first one exits, so the exit codes are read
    from the containers instead.

    Args:
        stack_client (DockerClient): The client of the compose file just started.

    Raises:
        RuntimeError: Naming the container and its exit code.
    """
    for container in stack_client.compose.ps(all=True):
        state = container.state
        if not state.running and state.exit_code:
            raise RuntimeError(f"{container.name} exited with code {state.exit_code}.")


def launch_stack(compose_filename: str, profiles: List[str]):
    """
    Start the stack via docker compose up.

    If the 'deps' profile is active, this blocks until the ephemeral init container
    finishes. Otherwise, it detaches and waits for healthchecks.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to launch.
    """
    stack_client = create_client(compose_filename, profiles)

    # The 'deps' profile contains an ephemeral container that exits after copying files.
    # Docker Compose's --wait flag fails if it sees a container exit (even with code 0).
    if "deps" in profiles:
        # detach=False blocks until the init container gracefully finishes its job
        stack_client.compose.up(detach=False)
        check_exit_codes(stack_client)
    else:
        # For all other long-running services, we detach and wait for healthchecks
        wait_for_one_shot_containers()
        stack_client.compose.up(detach=True, wait=True)


def stop_stack(
    compose_filename: str, profiles: List[str], remove_volumes: bool = False
):
    """
    Stop and remove containers and networks for a stack.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to stop.
        remove_volumes (bool, optional): If True, destroys the named volumes of the
                                         stack and the unnamed volumes of its
                                         containers. Defaults to False.
    """
    stack_client = create_client(compose_filename, profiles)
    # volumes=True removes the named volumes defined in the compose file and the
    # unnamed volumes of the containers it stops.
    # remove_orphans catches containers whose service no longer exists in the
    # compose file, which teardown would otherwise leave running forever: an
    # upgrade that drops or renames a service (ch-init-lite in 0.2.0, the
    # flink1-* services in 0.3.0) leaves the old container holding its name.
    stack_client.compose.down(volumes=remove_volumes, remove_orphans=True)


def get_declared_volumes(compose_filename: str) -> Dict[str, str]:
    """
    Map each volume a compose file declares, external ones too, to its Docker name.

    A service mounts a volume by its key, and Docker lists it by its name. A mount
    of one of these is a named volume. Any other volume a container mounts is an
    unnamed one, which Docker creates from the image's `VOLUME` line.

    The name is the entry's `name:`, interpolated as Compose does, because a
    workspace file can build it from variables. Without `name:`, Compose names the
    volume `<project>_<key>`, from the project name `get_project_name` gives, or
    `<key>` when the volume is external.

    Args:
        compose_filename (str): The name of the compose file to parse.

    Returns:
        Dict[str, str]: Each volume's key to its Docker name.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose = read_compose(compose_filename)
    env = interpolation_env(compose_filename)
    project = get_project_name(compose_filename)
    names = {}
    for key, spec in (compose.get("volumes") or {}).items():
        name = spec.get("name") if isinstance(spec, dict) else None
        external = isinstance(spec, dict) and spec.get("external")
        if name:
            names[key] = expand(str(name), env)
        elif external or not project:
            names[key] = key
        else:
            names[key] = f"{project}_{key}"
    return names


def get_volume_names() -> set:
    """
    Fetch the names of the volumes that exist, as `docker volume ls` lists them.

    Returns:
        set: The volume names.
    """
    return {volume.name for volume in client.volume.list()}


def get_managed_containers(execution_plan: Dict[str, List[str]]) -> List[Any]:
    """
    Fetch Docker containers matching the requested execution plan.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    A container counts when its Compose project is the project of one of the plan's
    files, as `get_project_name` names it, and its service is one of that file's. A
    workspace file can set its own `name:`, so the project need not start with
    `odctl-`.

    Returns:
        List[Any]: A list of python-on-whales Container objects managed by the ODCTL stack.

    Raises:
        ValueError: If a compose file of the plan cannot be read.
    """
    targets: Set[Tuple[str, str]] = set()
    for file, profs in execution_plan.items():
        project = get_project_name(file)
        # Re-using your existing parser to know exactly which services to look for
        services, _, _, _ = get_stack_details(file, profs)
        targets.update((project, service) for service in services)

    all_containers = client.container.list(all=True)
    managed_containers = []

    for c in all_containers:
        # Safely access labels via the Container's Config block
        labels = c.config.labels if c.config and c.config.labels else {}

        project = labels.get("com.docker.compose.project", "")
        service = labels.get("com.docker.compose.service", "")

        # The project and the service must both be those of one file of the plan.
        if (project, service) in targets:
            managed_containers.append(c)

    return managed_containers
