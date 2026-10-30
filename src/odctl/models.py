from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer


class Port(BaseModel):
    """
    A published port: the host port that reaches a container port.

    Attributes:
        host (int): The port on the host.
        container (int): The port inside the container.
        protocol (str): The transport protocol, `tcp` unless the source says otherwise.
    """

    host: int
    container: int
    protocol: str = "tcp"


class ServiceInfo(BaseModel):
    """
    A compose service that a profile starts.

    Attributes:
        name (str): The compose service name.
        image (Optional[str]): The image as it will run, with `TAG` resolved, or None
            when the service builds or inherits its image.
        ports (List[Port]): The ports the service publishes on the host that are plain
            numbers once compose variables are expanded, sorted by host port.
    """

    name: str
    image: Optional[str] = None
    ports: List[Port] = Field(default_factory=list)


class ProfileInfo(BaseModel):
    """
    One profile of the registry, as `odctl list` shows it.

    Attributes:
        profile (str): The profile name.
        stack (str): The stack the profile belongs to: the registry entry's `parent`,
            or its own id when it has none.
        description (str): What the stack provides.
        compose_file (str): The compose file that defines the profile's services.
        depends_on (List[str]): The profiles the registry lists as direct prerequisites.
        starts (List[str]): Every profile `odctl up` starts for this one, the profile
            itself and all its prerequisites.
        services (List[ServiceInfo]): The services the profile starts, sorted by name.
            Empty when the compose files were not read.
    """

    profile: str
    stack: str
    description: str
    compose_file: str
    depends_on: List[str]
    starts: List[str]
    services: List[ServiceInfo]
    # The registry's id of the stack, which the tables group by; not in the JSON.
    stack_id: str = Field(default="", exclude=True)
    # Every port as the compose file wrote it, as `service:port`, sorted, which the
    # tables print; not in the JSON.
    port_specs: List[str] = Field(default_factory=list, exclude=True)


class ProfileDetails(ProfileInfo):
    """
    One profile with everything `odctl explain` shows.

    Attributes:
        usage (Optional[str]): The usage text for this profile, or None when the
            registry has none for it.
        role (Optional[str]): The architectural role of the profile's stack.
        volumes (List[str]): The named volumes the profile's services mount.
    """

    usage: Optional[str] = None
    role: Optional[str] = None
    volumes: List[str] = Field(default_factory=list)
    # Whether the registry gives usage text for other profiles of the stack but not
    # this one, which the panel shows as a placeholder; not in the JSON.
    usage_missing: bool = Field(default=False, exclude=True)


class ContainerInfo(BaseModel):
    """
    A container that odctl manages.

    Attributes:
        name (str): The container name.
        service (Optional[str]): The compose service, or None when the container has no
            compose service label.
        state (str): The state as Docker reports it, for example `running` or `exited`.
        health (Optional[str]): The health status as Docker reports it, or None when
            the container has no health check.
        ports (List[Port]): The ports published on the host. The attribute keeps
            Docker's order, which the table shows; the JSON sorts them by host port,
            then container port and protocol.
    """

    name: str
    service: Optional[str] = None
    state: str
    health: Optional[str] = None
    ports: List[Port] = Field(default_factory=list)

    @field_serializer("ports")
    def _sorted_ports(self, ports: List[Port]) -> List[Port]:
        """
        Sort the ports for the JSON.

        Args:
            ports (List[Port]): The ports in Docker's order.

        Returns:
            List[Port]: The ports sorted by host port, then container port and protocol.
        """
        return sorted(ports, key=lambda p: (p.host, p.container, p.protocol))


class PsReport(BaseModel):
    """
    The containers `odctl ps` shows and the profiles they make active.

    Attributes:
        active_profiles (List[str]): Profiles whose services are all running, sorted.
        containers (List[ContainerInfo]): The matching containers, sorted by name.
    """

    active_profiles: List[str]
    containers: List[ContainerInfo]


class WorkspaceInfo(BaseModel):
    """
    The workspace folder odctl reads.

    Attributes:
        path (str): The workspace path.
        exists (bool): Whether the folder exists. When it does not, odctl reads the
            files bundled with the CLI.
        stale_tag (Optional[str]): The workspace's `TAG` when it differs from the CLI
            version, otherwise None.
    """

    path: str
    exists: bool
    stale_tag: Optional[str] = None


class DockerInfo(BaseModel):
    """
    The Docker daemon odctl talks to.

    Attributes:
        reachable (bool): Whether the daemon answers.
    """

    reachable: bool


class ImageInfo(BaseModel):
    """
    One of odctl's own images at the current tag.

    Attributes:
        reference (str): The full image reference.
        local (bool): Whether the image is on the Docker host. False when Docker is
            not reachable.
    """

    reference: str
    local: bool


class Info(BaseModel):
    """
    What `odctl info` shows.

    Attributes:
        cli_version (str): The installed odctl version.
        tag (str): `TAG` as Docker Compose resolves it.
        workspace (WorkspaceInfo): The workspace folder.
        docker (DockerInfo): The Docker daemon.
        images (List[ImageInfo]): odctl's own images at `tag` for every profile, sorted
            by reference.
    """

    cli_version: str
    tag: str
    workspace: WorkspaceInfo
    docker: DockerInfo
    images: List[ImageInfo]
