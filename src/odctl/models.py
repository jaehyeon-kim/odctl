from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class _JsonModel(BaseModel):
    """
    Base of every model that `--json` prints.

    `--json` always writes every field, so the schema marks every field as required.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Port(_JsonModel):
    """A published port: the host port that reaches a container port."""

    host: int = Field(description="The port on the host, a number.")
    container: int = Field(description="The port inside the container, a number.")
    protocol: str = Field(
        default="tcp",
        description="The transport protocol, `tcp` or `udp`, as Docker or the compose file gives it.",
    )


class ServiceInfo(_JsonModel):
    """A compose service that a profile starts."""

    name: str = Field(description="The compose service name.")
    image: Optional[str] = Field(
        default=None,
        description="The image as it will run, with `TAG` resolved. `null` when the compose file gives the service no `image`, as for a service that is built.",
    )
    ports: List[Port] = Field(
        default_factory=list,
        description="The ports the service publishes on the host, sorted by host port. Compose variables are expanded first, as compose does. A port range is left out, and so is a port with no host part, which compose publishes on a random host port. Empty when the service publishes none.",
    )


class ProfileInfo(_JsonModel):
    """One profile of the registry, as `odctl list` shows it."""

    profile: str = Field(description="The profile name, which `odctl up` takes.")
    stack: str = Field(
        description="The stack the profile belongs to, such as `kafka` for `kafka-lite`. When the registry gives the stack a `parent` group, the value is that group instead, such as `infra` for `postgres`, `storage` and `catalog`."
    )
    description: str = Field(description="What the stack provides.")
    compose_file: str = Field(
        description="The compose file that defines the profile's services."
    )
    depends_on: List[str] = Field(
        description="The profiles the registry lists as direct prerequisites, sorted by name. Empty when there are none."
    )
    starts: List[str] = Field(
        description="Every profile `odctl up` starts for this one: the profile itself and all its prerequisites, sorted by name."
    )
    services: List[ServiceInfo] = Field(
        description="The services the profile starts, sorted by name."
    )
    # Stack id from the registry, which the tables group by; not in the JSON.
    stack_id: str = Field(default="", exclude=True)
    # Every port as the compose file wrote it, as `service:port`, sorted, which the
    # tables print; not in the JSON.
    port_specs: List[str] = Field(default_factory=list, exclude=True)


class ProfileDetails(ProfileInfo):
    """One profile with everything `odctl explain` shows."""

    usage: Optional[str] = Field(
        default=None,
        description="The text that says how to reach the profile's services. `null` when the registry has none for this profile.",
    )
    role: Optional[str] = Field(
        default=None,
        description="What the profile's stack does in a data platform. `null` when the registry gives none.",
    )
    volumes: List[str] = Field(
        default_factory=list,
        description="The named volumes the profile's services mount, sorted by name. Bind mounts are left out, and so are volumes the compose file declares as `external`, so `odctl-shared-deps` appears only for the `deps` profile. Empty when there are none.",
    )
    # Whether the registry gives usage text for other profiles of the stack but not
    # this one, which the panel shows as a placeholder; not in the JSON.
    usage_missing: bool = Field(default=False, exclude=True)


class ContainerInfo(_JsonModel):
    """A container that odctl manages."""

    name: str = Field(description="The container name.")
    service: Optional[str] = Field(
        default=None,
        description="The compose service. `null` when the container has no compose service label.",
    )
    state: str = Field(
        description="The state as Docker reports it, for example `running` or `exited`."
    )
    health: Optional[str] = Field(
        default=None,
        description="The health status as Docker reports it, for example `healthy`. `null` when the container has no health check.",
    )
    ports: List[Port] = Field(
        default_factory=list,
        description="The ports published on the host, sorted by host port, then container port and protocol. Empty when the container publishes none.",
    )

    @field_serializer("ports")
    def _sorted_ports(self, ports: List[Port]) -> List[Port]:
        """
        Sort the ports for the JSON.

        Args:
            ports (List[Port]): The ports in Docker's order, which the table shows.

        Returns:
            List[Port]: The ports sorted by host port, then container port and protocol.
        """
        return sorted(ports, key=lambda p: (p.host, p.container, p.protocol))


class PsReport(_JsonModel):
    """The containers `odctl ps` shows and the profiles they make active."""

    active_profiles: List[str] = Field(
        description="The profiles whose services are all running, sorted. Only the profiles the command names are considered, with their prerequisites in the same compose file, such as `postgres` and `storage` for `catalog`. With `--all`, every profile is considered. `deps` is never listed. A profile whose services are a strict subset of another listed profile's is left out, so `spark-lite` is not listed beside `spark-full`. Empty when no profile is fully running."
    )
    containers: List[ContainerInfo] = Field(
        description="The matching containers, sorted by name. Empty when none match."
    )


class WorkspaceInfo(_JsonModel):
    """The workspace folder odctl reads."""

    path: str = Field(description="The workspace path, an absolute path.")
    exists: bool = Field(
        description="Whether the folder exists. When it does not, odctl reads the files bundled with the CLI."
    )
    stale_tag: Optional[str] = Field(
        default=None,
        description="The workspace's `TAG` when it differs from the CLI version and no `TAG` is set in the shell. Otherwise `null`.",
    )


class DockerInfo(_JsonModel):
    """The Docker daemon odctl talks to."""

    reachable: bool = Field(description="Whether the daemon answers.")


class ImageInfo(_JsonModel):
    """One of odctl's own images at the current tag."""

    reference: str = Field(description="The full image reference, with its tag.")
    local: bool = Field(
        description="Whether the image is already on the Docker host. `false` when Docker is not reachable."
    )


class Info(_JsonModel):
    """What `odctl info` shows."""

    cli_version: str = Field(description="The installed odctl version.")
    tag: str = Field(description="`TAG` as Docker Compose resolves it.")
    workspace: WorkspaceInfo = Field(description="The workspace folder.")
    docker: DockerInfo = Field(description="The Docker daemon.")
    images: List[ImageInfo] = Field(
        description="odctl's own images at `tag` for every profile, sorted by reference."
    )
