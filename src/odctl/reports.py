from typing import Any, Dict, List, Optional, Tuple

from odctl import config, docker, planner, workspace
from odctl.models import (
    ContainerInfo,
    DockerInfo,
    ImageInfo,
    Info,
    Port,
    ProfileDetails,
    ProfileInfo,
    PsReport,
    ServiceInfo,
    WorkspaceInfo,
)
from odctl.registry import Registry, load_registry


class UnknownProfileError(Exception):
    """Raised when a profile is not in the registry."""


def _compose_unreadable(compose_file: str, services: List[str]) -> Optional[str]:
    """
    Report why `get_stack_details` could not read a compose file.

    Args:
        compose_file (str): The compose file that was read.
        services (List[str]): The services `get_stack_details` returned for it.

    Returns:
        Optional[str]: A message when the services are the error marker that
        `get_stack_details` returns for a missing or unparseable file, otherwise None.
    """
    if services and (services[0] == "File Error" or services[0].startswith("Err: ")):
        return f"Cannot read {compose_file}: {services[0]}"
    return None


def _parse_port(spec: str) -> Optional[Port]:
    """
    Read a compose port such as `127.0.0.1:8084:8083` or `8080:80/udp`.

    Args:
        spec (str): The port as `get_stack_details` returns it, without the service,
            with compose variables already expanded.

    Returns:
        Optional[Port]: The port, or None when it is not made of plain numbers, as with
        a range.
    """
    numbers, _, protocol = spec.partition("/")
    parts = numbers.split(":")
    try:
        container = int(parts[-1])
        host = int(parts[-2]) if len(parts) >= 2 else container
    except ValueError:
        return None
    return Port(host=host, container=container, protocol=protocol or "tcp")


def _read_stack(
    compose_file: str, profile: str, for_json: bool
) -> Tuple[List[ServiceInfo], List[str], List[str]]:
    """
    Read the services, raw ports and volumes of a profile from its compose file.

    Args:
        compose_file (str): The compose file that defines the profile.
        profile (str): The profile name.
        for_json (bool): True to fail when the file cannot be read. False to keep the
            error marker of `get_stack_details` as the only service, port and volume, as
            the tables show it.

    Returns:
        Tuple[List[ServiceInfo], List[str], List[str]]: The services, sorted by name,
        each with its ports sorted by host port; the ports as the compose file wrote
        them, as `service:port`; and the named volumes.

    Raises:
        ValueError: If `for_json` is set and the compose file cannot be read.
    """
    names, specs, images, volumes = docker.get_stack_details(compose_file, [profile])
    unreadable = _compose_unreadable(compose_file, names)
    if unreadable:
        if for_json:
            raise ValueError(unreadable)
        return [ServiceInfo(name=names[0])], specs, volumes

    image_of: Dict[str, str] = {}
    for entry in images:
        name, _, image = entry.partition(" -> ")
        image_of[name] = image

    # Compose expands variables in a port before it reads it.
    env = docker.interpolation_env()
    ports_of: Dict[str, List[Port]] = {name: [] for name in names}
    for entry in specs:
        name, _, spec = entry.partition(":")
        port = _parse_port(docker.expand(spec, env))
        if port is not None and name in ports_of:
            ports_of[name].append(port)

    services = [
        ServiceInfo(
            name=name,
            image=image_of.get(name),
            ports=sorted(
                ports_of[name], key=lambda p: (p.host, p.container, p.protocol)
            ),
        )
        for name in names
    ]
    return services, specs, volumes


def _starts(
    registry: Registry, profile_map: Dict[str, dict], profile: str
) -> List[str]:
    """
    List every profile `odctl up` starts for a profile.

    Args:
        registry (Registry): The loaded registry.
        profile_map (Dict[str, dict]): The profile to stack lookup from the planner.
        profile (str): The profile name.

    Returns:
        List[str]: The profile and all its prerequisites, sorted.

    Raises:
        ValueError: If the registry lists a dependency that no stack defines.
    """
    try:
        return sorted(planner.resolve_dependencies([profile], profile_map, registry))
    except KeyError as unknown:
        raise ValueError(
            f"Cannot work out what '{profile}' starts: the registry lists the "
            f"profile {unknown} as a dependency, and no stack defines it."
        ) from unknown


def _profile_info(
    registry: Registry,
    profile_map: Dict[str, dict],
    profile: str,
    services: List[ServiceInfo],
    port_specs: List[str],
    with_starts: bool,
) -> ProfileInfo:
    """
    Build the list entry of one profile.

    Args:
        registry (Registry): The loaded registry.
        profile_map (Dict[str, dict]): The profile to stack lookup from the planner.
        profile (str): The profile name.
        services (List[ServiceInfo]): The services read from the compose file, or none.
        port_specs (List[str]): The ports as the compose file wrote them, or none.
        with_starts (bool): Whether to work out `starts`, which fails for a registry
            that lists an unknown dependency.

    Returns:
        ProfileInfo: The profile's entry.

    Raises:
        ValueError: If `with_starts` is set and the registry lists an unknown dependency.
    """
    stack_id = profile_map[profile]["stack_id"]
    stack = registry.stacks[stack_id]
    return ProfileInfo(
        profile=profile,
        stack=stack.parent or stack_id,
        description=stack.description,
        compose_file=stack.file,
        depends_on=sorted(stack.depends_on.get(profile, [])),
        starts=_starts(registry, profile_map, profile) if with_starts else [],
        services=services,
        stack_id=stack_id,
        port_specs=port_specs,
    )


def build_profiles(for_json: bool, with_services: bool = True) -> List[ProfileInfo]:
    """
    Build the entry of every profile, in registry order.

    Args:
        for_json (bool): True for the JSON, which works out `starts` and fails when a
            compose file cannot be read. False for the tables, which leave `starts`
            empty and show an unreadable compose file as the error marker.
        with_services (bool): Whether to read the compose files for each profile's
            services and ports. Defaults to True.

    Returns:
        List[ProfileInfo]: One entry per profile.

    Raises:
        FileNotFoundError: If the registry file does not exist.
        ValueError: If `for_json` is set and a compose file cannot be read or the
            registry lists an unknown dependency.
    """
    registry = load_registry()
    profile_map = planner.get_profile_map()
    profiles = []
    for stack in registry.stacks.values():
        for profile in stack.profiles:
            services: List[ServiceInfo] = []
            port_specs: List[str] = []
            if with_services:
                services, port_specs, _ = _read_stack(stack.file, profile, for_json)
            profiles.append(
                _profile_info(
                    registry,
                    profile_map,
                    profile,
                    services,
                    port_specs,
                    with_starts=for_json,
                )
            )
    return profiles


def build_profile_details(profile: str, for_json: bool) -> ProfileDetails:
    """
    Build the details of one profile.

    Args:
        profile (str): The profile name.
        for_json (bool): True to fail when the compose file cannot be read. False to
            show it as the error marker, as the panel does.

    Returns:
        ProfileDetails: The profile's entry with its usage text, role and volumes.

    Raises:
        FileNotFoundError: If the registry file does not exist.
        UnknownProfileError: If the registry has no such profile.
        ValueError: If `for_json` is set and the compose file cannot be read, or the
            registry lists an unknown dependency.
    """
    registry = load_registry()
    profile_map = planner.get_profile_map()
    if profile not in profile_map:
        raise UnknownProfileError(profile)

    stack = registry.stacks[profile_map[profile]["stack_id"]]
    services, port_specs, volumes = _read_stack(stack.file, profile, for_json)
    info = _profile_info(
        registry, profile_map, profile, services, port_specs, with_starts=True
    )

    usage = stack.usage
    usage_missing = False
    if isinstance(usage, dict):
        usage_missing = profile not in usage
        usage = usage.get(profile)

    return ProfileDetails(
        **{name: getattr(info, name) for name in ProfileInfo.model_fields},
        usage=usage,
        role=stack.role,
        volumes=volumes,
        usage_missing=usage_missing,
    )


def _container_info(container) -> ContainerInfo:
    """
    Read one python-on-whales container into a model.

    Args:
        container: A python-on-whales Container object.

    Returns:
        ContainerInfo: The container's name, service, state, health and ports.
    """
    labels = container.config.labels if container.config else None
    service = (labels or {}).get("com.docker.compose.service") or None
    health = container.state.health.status if container.state.health else None

    ports: List[Port] = []
    if container.network_settings and container.network_settings.ports:
        for container_port, bindings in container.network_settings.ports.items():
            number, _, protocol = container_port.partition("/")
            for binding in bindings or []:
                host_port = binding.get("HostPort")
                if not host_port:
                    continue
                port = Port(
                    host=int(host_port),
                    container=int(number),
                    protocol=protocol or "tcp",
                )
                if port not in ports:
                    ports.append(port)

    return ContainerInfo(
        name=container.name,
        service=service,
        state=container.state.status,
        health=health,
        ports=ports,
    )


def _active_profiles(plan: Dict[str, List[str]], containers: List[Any]) -> List[str]:
    """
    Find the profiles whose services are all running.

    A profile whose services are a strict subset of another active profile's is
    left out, so `kafka-lite` does not also list the profiles it contains. The
    shared `deps` profile is never listed.

    Args:
        plan (Dict[str, List[str]]): A mapping of compose files to the profiles asked for.
        containers (List[Any]): The managed python-on-whales containers.

    Returns:
        List[str]: The active profiles, sorted.
    """
    running_services = set()
    for c in containers:
        labels = c.config.labels if c.config and c.config.labels else {}
        service = labels.get("com.docker.compose.service", "")
        if service:
            running_services.add(service)

    active: Dict[str, set] = {}
    for file, profiles in plan.items():
        for profile in profiles:
            services = docker.get_stack_details(file, [profile])[0]
            if services and all(s in running_services for s in services):
                active[profile] = set(services)

    outermost = {
        profile
        for profile, services in active.items()
        if not any(
            profile != other and services < other_services
            for other, other_services in active.items()
        )
    }
    outermost.discard("deps")
    return sorted(outermost)


def build_ps(profiles: Optional[List[str]], all_profiles: bool) -> PsReport:
    """
    Build the report of the containers odctl manages.

    Args:
        profiles (Optional[List[str]]): The profiles whose containers to include.
        all_profiles (bool): Include every container odctl manages.

    Returns:
        PsReport: The active profiles and the matching containers.

    Raises:
        typer.Exit: If no profile is given with `all_profiles` unset, or a profile is
            unknown. The planner prints the error first.
    """
    # Only what was asked for, widened just enough that compose accepts the project.
    plan = planner.expand_plan_dependencies(
        planner.build_execution_plan(profiles, all_profiles, resolve_deps=False)
    )
    containers = docker.get_managed_containers(plan)
    return PsReport(
        active_profiles=_active_profiles(plan, containers),
        containers=sorted(
            (_container_info(c) for c in containers), key=lambda c: c.name
        ),
    )


def build_info(include_images: bool = True) -> Info:
    """
    Build the report `odctl info` shows.

    Args:
        include_images (bool): Whether to list odctl's own images and check each one
            on the host, which takes a Docker call per image. Defaults to True.

    Returns:
        Info: The version, tag, workspace, Docker state and, when asked, the images.

    Raises:
        FileNotFoundError: If `include_images` is set and the registry file does not exist.
    """
    reachable = docker.is_docker_running()

    images: List[ImageInfo] = []
    if include_images:
        plan = planner.build_execution_plan(all_profiles=True)
        images = [
            ImageInfo(
                reference=reference,
                local=reachable and docker.image_is_local(reference),
            )
            for reference in docker.get_versioned_images(plan)
        ]

    workspace_dir = config.get_workspace_dir()
    return Info(
        cli_version=workspace.get_cli_version(),
        tag=docker.resolve_image_tag(),
        workspace=WorkspaceInfo(
            path=str(workspace_dir),
            exists=workspace_dir.exists(),
            stale_tag=workspace.stale_workspace_tag(),
        ),
        docker=DockerInfo(reachable=reachable),
        images=images,
    )
