"""The langfuse profile runs Langfuse's web and worker services on odctl's own
PostgreSQL, ClickHouse, Valkey and SeaweedFS. Nothing here needs Docker.
"""

import re
from pathlib import Path

import yaml

from odctl.config import get_internal_resources_dir
from odctl.planner import build_execution_plan

RESOURCES = get_internal_resources_dir()
REPO = Path(__file__).resolve().parents[1]

# The buckets storage created in 1.5.0, before langfuse joined them.
BUCKETS_IN_1_5_0 = [
    "warehouse",
    "odctl-dev",
    "flink-checkpoints",
    "flink-savepoints",
    "airflow",
    "mlflow",
    "feast",
    "openmetadata",
]


def _compose(name):
    return yaml.safe_load((RESOURCES / name).read_text())["services"]


def _langfuse(name):
    return _compose("compose-aieng.yml")[name]


def _buckets():
    init = _compose("compose-infra.yml")["seaweed-init"]
    return re.search(r"BUCKETS='([^']*)'", init["entrypoint"]).group(1).split()


def _heap_mib(service):
    options = service["environment"]["NODE_OPTIONS"]
    return int(re.search(r"--max-old-space-size=(\d+)", options).group(1))


def test_the_ui_is_on_host_port_3005_and_the_worker_publishes_no_port():
    assert _langfuse("langfuse-web")["ports"] == ["127.0.0.1:3005:3000"]
    assert "ports" not in _langfuse("langfuse-worker")


def test_clickhouse_runs_without_a_cluster_and_the_compose_file_has_no_init_service():
    env = _langfuse("langfuse-web")["environment"]
    assert env["CLICKHOUSE_CLUSTER_ENABLED"] == "false"
    assert env["CLICKHOUSE_DB"] == "langfuse"
    assert set(_compose("compose-aieng.yml")) == {"langfuse-web", "langfuse-worker"}


def test_the_init_files_create_the_langfuse_database():
    postgres = (RESOURCES / "postgres" / "01-init-databases.sh").read_text()
    assert 'CREATE DATABASE langfuse OWNER "$POSTGRES_USER";' in postgres
    assert re.search(r"^for db in .*\blangfuse\b.*; do$", postgres, re.M)
    clickhouse = (RESOURCES / "clickhouse" / "init.sql").read_text()
    assert "CREATE DATABASE IF NOT EXISTS langfuse;" in clickhouse


def test_langfuse_logs_in_to_valkey_as_the_user_with_the_default_user_off():
    env = _langfuse("langfuse-worker")["environment"]
    assert env["REDIS_USERNAME"] == "user"
    assert env["REDIS_AUTH"] == "password"
    command = _compose("compose-store.yml")["valkey"]["command"]
    assert command[command.index("default") + 1] == "off"


def test_storage_keeps_its_buckets_and_adds_the_langfuse_bucket():
    assert _buckets() == BUCKETS_IN_1_5_0 + ["langfuse"]
    env = _langfuse("langfuse-web")["environment"]
    assert env["LANGFUSE_S3_EVENT_UPLOAD_BUCKET"] == "langfuse"


def test_usage_telemetry_is_off_and_the_heap_is_three_quarters_of_the_limit():
    for name in ("langfuse-web", "langfuse-worker"):
        service = _langfuse(name)
        assert service["environment"]["TELEMETRY_ENABLED"] == "false"
        limit_mib = int(service["mem_limit"].rstrip("g")) * 1024
        assert _heap_mib(service) == limit_mib * 3 // 4


def test_langfuse_has_a_smoke_case():
    smoke = (REPO / ".github" / "scripts" / "smoke.sh").read_text()
    assert re.search(r"^  langfuse\)\s+smoke_langfuse\b", smoke, re.M)


def test_valkey_starts_before_langfuse():
    plan = list(build_execution_plan(profiles=["langfuse"]))
    assert plan.index("compose-store.yml") < plan.index("compose-aieng.yml")
