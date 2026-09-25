"""Metrics endpoints for Kafka, Connect, Trino, Metabase, Fluss, SeaweedFS and the catalog.

Each service exposes Prometheus metrics without an extra exporter container: a
native endpoint where the service has one, and the Prometheus JMX exporter agent
from the shared volume where it does not. These checks pin the settings that turn
each endpoint on. Nothing here needs Docker.
"""

import json

import yaml

from odctl.config import get_internal_resources_dir

RES = get_internal_resources_dir()
AGENT = "-javaagent:/mnt/shared-deps/agents/jmx_prometheus_javaagent.jar=9404:/etc/jmx/jmx-exporter.yml"


def _services(name):
    return yaml.safe_load((RES / name).read_text())["services"]


def test_every_kafka_broker_runs_the_jmx_agent():
    services = _services("compose-kafka.yml")
    for broker in ("kafka", "kafka-1", "kafka-2", "kafka-3"):
        env = services[broker]["environment"]
        # Given to the broker process only: in the environment as KAFKA_OPTS, every
        # CLI tool run with `docker exec` would load the agent, fail to bind 9404
        # and exit.
        assert env["ODCTL_JMX_AGENT"] == AGENT, broker
        assert "KAFKA_OPTS" not in env, broker
        assert (
            'KAFKA_OPTS="$$ODCTL_JMX_AGENT" exec /etc/kafka/docker/run'
            in services[broker]["command"][-1]
        ), broker
        assert "./jmx:/etc/jmx:ro" in services[broker]["volumes"], broker
        assert "odctl-shared-deps:/mnt/shared-deps:ro" in services[broker]["volumes"], (
            broker
        )


def test_connect_runs_the_jmx_agent():
    connect = _services("compose-kafka.yml")["connect"]
    assert connect["environment"]["ODCTL_JMX_AGENT"] == AGENT
    assert "KAFKA_OPTS" not in connect["environment"]
    assert (
        'KAFKA_OPTS="$$ODCTL_JMX_AGENT" /opt/kafka/bin/connect-distributed.sh'
        in connect["command"]
    )
    assert "./jmx:/etc/jmx:ro" in connect["volumes"]


def test_catalog_runs_the_jmx_agent():
    catalog = _services("compose-infra.yml")["catalog"]
    assert AGENT in catalog["command"]
    assert catalog["command"].index(AGENT) < catalog["command"].index("-cp")
    assert "./jmx:/etc/jmx:ro" in catalog["volumes"]


def test_seaweedfs_serves_metrics():
    assert "-metricsPort=9327" in _services("compose-infra.yml")["seaweed"]["command"]


def test_metabase_serves_metrics():
    assert (
        _services("compose-analytics.yml")["metabase"]["environment"][
            "MB_PROMETHEUS_SERVER_PORT"
        ]
        == 9191
    )


def test_fluss_servers_use_the_prometheus_reporter():
    services = _services("compose-store.yml")
    for name in ("fluss-coordinator", "fluss-tablet-1"):
        props = next(
            e
            for e in services[name]["environment"]
            if e.startswith("FLUSS_PROPERTIES=")
        )
        assert "metrics.reporters: prometheus" in props, name
        assert "metrics.reporter.prometheus.port: 9249" in props, name


def test_trino_lets_prometheus_read_system_information():
    rules = json.loads((RES / "trino" / "rules.json").read_text())
    assert {"user": "prometheus", "allow": ["read"]} in rules["system_information"]


def test_the_deps_image_ships_the_agent_outside_the_classpath_folders():
    fetch = (RES / "deps" / "fetch_standalone_plugins.sh").read_text()
    assert 'fetch_artifact "agents/jmx_prometheus_javaagent.jar"' in fetch
    assert (
        "COPY --from=downloader /downloads/agents /workspace/agents/"
        in (RES / "deps" / "Dockerfile").read_text()
    )
    assert "JMX_EXPORTER_V=" in (RES / "deps" / "versions.env").read_text()


def test_the_jmx_exporter_config_exists():
    assert (
        yaml.safe_load((RES / "jmx" / "jmx-exporter.yml").read_text())[
            "lowercaseOutputName"
        ]
        is True
    )
