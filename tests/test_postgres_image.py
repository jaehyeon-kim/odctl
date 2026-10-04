"""The postgres profile runs odctl's own image: PostgreSQL 18 with pgvector,
pg_textsearch and PostGIS.

pg_textsearch fails at CREATE EXTENSION unless it is preloaded, and the init
script creates all three extensions, so the compose command, the init script and
the image have to agree. Nothing here needs Docker.
"""

from pathlib import Path

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()
REPO = Path(__file__).resolve().parents[1]


def _postgres():
    return yaml.safe_load((RESOURCES / "compose-infra.yml").read_text())["services"][
        "postgres"
    ]


def _setting(name):
    command = _postgres()["command"]
    prefix = f"{name}="
    return next(arg[len(prefix) :] for arg in command if arg.startswith(prefix))


def test_postgres_uses_the_odctl_image():
    assert _postgres()["image"] == "ghcr.io/jaehyeon-kim/odctl/postgres:${TAG:-latest}"


def test_pg_textsearch_is_preloaded_with_pg_stat_statements():
    assert _setting("shared_preload_libraries").split(",") == [
        "pg_stat_statements",
        "pg_textsearch",
    ]


def test_init_script_creates_the_three_extensions_in_the_vector_database():
    script = (RESOURCES / "postgres" / "01-init-databases.sh").read_text()
    for extension in ("vector", "pg_textsearch", "postgis"):
        assert f"CREATE EXTENSION IF NOT EXISTS {extension};" in script


def test_image_builds_on_the_official_postgres_18_image():
    dockerfile = (RESOURCES / "docker" / "postgres" / "Dockerfile").read_text()
    assert dockerfile.startswith("FROM postgres:18-trixie\n")
    for arg in ("ARG PGVECTOR_V=", "ARG PG_TEXTSEARCH_V=", "ARG TARGETARCH"):
        assert arg in dockerfile
    assert "postgresql-${PG_MAJOR}-postgis-3" in dockerfile


def test_image_is_built_and_published_with_the_others():
    workflow = (
        REPO / ".github" / "workflows" / "build-platform-images.yml"
    ).read_text()
    assert workflow.count("component: [airflow, mlflow, postgres, spark]") == 2
