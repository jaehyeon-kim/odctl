"""Checks on the role `odctl explain` gives each container.

`odctl explain` names a role for each service by matching its image against
`CONTAINER_ROLES` with `container_role`. Before 1.10.0, six images had no key, so
their services showed the fallback "Service Container" and said nothing about what
they do, and a key matched any image that held it, so the order of the keys decided
the roles.
"""

import yaml

from odctl.config import get_internal_resources_dir
from odctl.ui import CONTAINER_ROLES, container_role

# The table and the matching of 1.9.0 (`ui.py` at v1.9.0), to check that every
# image with a role then keeps it.
ROLES_1_9_0 = {
    "odctl/postgres": "PostgreSQL with pgvector, pg_textsearch and PostGIS",
    "seaweedfs": "Object Storage (S3 API)",
    "zulu-openjdk": "Iceberg REST Catalog",
    "odctl/deps": "Dependency Initializer",
    "flink": "Flink Stream Processing Node",
    "apache/kafka": "Event Broker / Kafka Connect",
    "karapace": "Schema Registry",
    "kafka-ui": "Kafka Dashboard",
    "elasticsearch": "OpenMetadata Search Backend",
    "openmetadata/server": "OpenMetadata Server",
    "openmetadata/ingestion": "OpenMetadata Ingestion Pipeline",
    "odctl/airflow": "Airflow Orchestrator",
    "odctl/mlflow": "MLflow Tracking and Model Server",
    "evidently-service": "ML Monitoring (Evidently UI)",
    "temporalio/temporal": "Temporal Development Server and Web UI",
    "marquez-web": "Lineage Dashboard",
    "marquezproject/marquez": "Lineage API Server",
    "otel-lgtm": "Telemetry: OTLP, Prometheus, Tempo, Loki, Grafana",
    "odctl/spark": "Spark Processing Node",
    "clickhouse-keeper": "Consensus Node",
    "clickhouse-server": "Analytical Database (OLAP)",
    "fluss": "Streaming Storage Engine",
    "valkey": "In-Memory Cache & Vector DB",
    "trinodb/trino": "Federated SQL Engine",
    "metabase": "BI Dashboard",
}


def _images():
    """Returns every image of the packaged compose files, with the service that uses it."""
    images = {}
    for path in sorted(get_internal_resources_dir().glob("compose-*.yml")):
        services = (yaml.safe_load(path.read_text()) or {}).get("services") or {}
        for name, service in services.items():
            if service.get("image"):
                images.setdefault(service["image"], name)
    return images


def _repository(image):
    """Returns the image without its tag."""
    slash = image.rfind("/")
    colon = image.find(":", slash + 1)
    return image if colon == -1 else image[:colon]


def test_every_packaged_image_matches_exactly_one_key():
    matches = {
        image: [
            key
            for key in CONTAINER_ROLES
            if _repository(image) == key or _repository(image).endswith("/" + key)
        ]
        for image in _images()
    }
    assert {image: keys for image, keys in matches.items() if len(keys) != 1} == {}
    assert all(container_role(image) for image in _images())


def test_every_role_key_matches_a_packaged_image():
    images = _images()
    unused = [
        key
        for key in CONTAINER_ROLES
        if not any(container_role(image) == CONTAINER_ROLES[key] for image in images)
    ]
    assert unused == []


def test_the_images_with_a_role_in_1_9_0_keep_it():
    """The "Must not change (batch 2)" row: the images that had a role keep it."""
    kept = {}
    for image in _images():
        old = next((r for k, r in ROLES_1_9_0.items() if k in image), None)
        if old is not None:
            kept[image] = (old, container_role(image))
    assert len(kept) == 25
    assert {image: roles for image, roles in kept.items() if roles[0] != roles[1]} == {}


def test_a_key_matches_whole_path_segments():
    """With substring matching, `marquezproject/marquez` would give the web image the
    API server's role, and `alpine` would match every `-alpine` tag."""
    assert container_role("marquezproject/marquez-web:0.51.1") == "Lineage Dashboard"
    assert container_role("marquezproject/marquez:0.51.1") == "Lineage API Server"
    assert container_role("clickhouse/clickhouse-server:25.12-alpine") == (
        "Analytical Database (OLAP)"
    )
    assert container_role("langfuse/langfuse-worker:4.72.0") == (
        "Langfuse Background Worker"
    )
    assert container_role("localhost:5000/apache/kafka:4.3.2") == (
        "Event Broker / Kafka Connect"
    )
    digest = "@sha256:" + "a" * 64
    for image in (
        f"apache/kafka{digest}",
        f"localhost:5000/apache/kafka:4.3.2{digest}",
    ):
        assert container_role(image) == "Event Broker / Kafka Connect", image
    assert container_role("example/unknown:1") is None
