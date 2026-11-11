"""A fixed workspace and fixed containers for tests that pin what the commands print.

The registry and compose files name every image in full, so a new image version
does not change the expected text, and the containers are plain objects, so no
Docker daemon is read.
"""

from pathlib import Path
from types import SimpleNamespace

REGISTRY = """\
stacks:
  base:
    file: compose-base.yml
    description: Shared network and setup.
    profiles: [base]
    depends_on:
      base: []
  kafka:
    file: compose-kafka.yml
    description: Event streaming for the tests.
    parent: streaming
    role: A broker with a dashboard.
    profiles: [kafka-lite, kafka-full]
    depends_on:
      kafka-lite: [base]
      kafka-full: [base]
    usage:
      kafka-lite: |
        Dashboard: http://127.0.0.1:8086
        Install with pip install feast[duckdb].
      kafka-full: Three brokers.
  cache:
    file: compose-cache.yml
    description: An in-memory cache.
    parent: streaming
    profiles: [valkey]
    depends_on:
      valkey: [kafka-lite]
"""

COMPOSE_BASE = """\
services:
  init-base:
    image: example/base:1.0
    profiles: [base]
"""

COMPOSE_KAFKA = """\
services:
  kafka:
    image: apache/kafka:4.3.2
    ports:
      - "127.0.0.1:9092:9092"
    profiles: [kafka-lite]
  kafka-1:
    image: apache/kafka:4.3.2
    ports:
      - "127.0.0.1:9093:9092"
    profiles: [kafka-full]
  kafka-ui:
    image: ghcr.io/kafbat/kafka-ui:v1.5.0
    ports:
      - "127.0.0.1:8086:8080"
    volumes:
      - ui-data:/data
    profiles: [kafka-lite, kafka-full]
volumes:
  ui-data:
"""

COMPOSE_CACHE = """\
services:
  valkey:
    image: valkey/valkey:8
    ports:
      - "127.0.0.1:6379:6379"
      - "127.0.0.1:16379:6380/udp"
    profiles: [valkey]
"""


def write_workspace(root: Path) -> Path:
    """
    Write the fixed registry and compose files to `root/.odctl`.

    Args:
        root (Path): The folder that holds the workspace.

    Returns:
        Path: The workspace folder.
    """
    workspace = root / ".odctl"
    workspace.mkdir()
    (workspace / "registry.yml").write_text(REGISTRY)
    (workspace / "compose-base.yml").write_text(COMPOSE_BASE)
    (workspace / "compose-kafka.yml").write_text(COMPOSE_KAFKA)
    (workspace / "compose-cache.yml").write_text(COMPOSE_CACHE)
    return workspace


def fake_container(
    name: str,
    service,
    state: str,
    health,
    ports,
    mounts=(),
):
    """
    Build an object with the attributes of a python-on-whales container that odctl reads.

    Args:
        name (str): The container name.
        service: The compose service label, or None for a container without one.
        state (str): The state Docker reports.
        health: The health status, or None for a container with no health check.
        ports: The `network_settings.ports` map, from container port to bindings.
        mounts: The `(type, name)` of each mount, such as `("volume", "abc123")`.
            Defaults to none.

    Returns:
        SimpleNamespace: The fake container.
    """
    labels = {"com.docker.compose.service": service} if service else {}
    return SimpleNamespace(
        name=name,
        config=SimpleNamespace(labels=labels),
        state=SimpleNamespace(
            status=state,
            health=SimpleNamespace(status=health) if health else None,
        ),
        network_settings=SimpleNamespace(ports=ports),
        mounts=[SimpleNamespace(type=t, name=n) for t, n in mounts],
    )


def fake_containers():
    """
    Build the containers of a running `kafka-lite`, a broken one and an unlabelled one.

    Returns:
        list: Fake containers, in an order that is not sorted by name.
    """
    return [
        fake_container(
            "kafka-ui",
            "kafka-ui",
            "running",
            "healthy",
            {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8086"}]},
        ),
        fake_container(
            "kafka",
            "kafka",
            "running",
            "starting",
            {
                "9092/tcp": [
                    {"HostIp": "127.0.0.1", "HostPort": "9092"},
                    {"HostIp": "::1", "HostPort": "9092"},
                ],
                "9093/tcp": None,
            },
        ),
        fake_container("init-base", "init-base", "exited", None, {}),
        fake_container("odd", None, "restarting", "unhealthy", None),
    ]
