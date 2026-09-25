"""The telemetry profile is one grafana/otel-lgtm container.

It replaced separate Prometheus, Alertmanager and Grafana services in 0.8.0. These
checks pin the shape callers rely on: one service, the published ports, the network
aliases that keep http://prometheus:9090 and http://grafana:3000 resolving, and the
scrape config mounted where the image reads it. Nothing here needs Docker.
"""

import yaml

from odctl.config import get_internal_resources_dir


def _compose():
    return yaml.safe_load(
        (get_internal_resources_dir() / "compose-obsv.yml").read_text()
    )


def _telemetry_services():
    services = _compose()["services"]
    return {
        n: s for n, s in services.items() if "telemetry" in (s.get("profiles") or [])
    }


def test_telemetry_is_one_service():
    services = _telemetry_services()
    assert list(services) == ["otel-lgtm"]
    assert services["otel-lgtm"]["image"].startswith("grafana/otel-lgtm:")


def test_telemetry_publishes_prometheus_grafana_and_otlp():
    ports = _telemetry_services()["otel-lgtm"]["ports"]
    published = {str(p).split(":")[0] for p in ports}
    assert published == {"19090", "3004", "4317", "4318"}


def test_old_hostnames_still_resolve():
    networks = _telemetry_services()["otel-lgtm"]["networks"]
    assert set(networks["odctl"]["aliases"]) >= {"prometheus", "grafana"}


def test_scrape_config_is_mounted_where_the_image_reads_it():
    volumes = _telemetry_services()["otel-lgtm"]["volumes"]
    assert "./prometheus/prometheus.yml:/otel-lgtm/prometheus.yaml" in volumes
    config = yaml.safe_load(
        (get_internal_resources_dir() / "prometheus" / "prometheus.yml").read_text()
    )
    jobs = {job["job_name"] for job in config["scrape_configs"]}
    assert {"prometheus", "flink", "clickhouse"} <= jobs
    assert "alerting" not in config


def test_grafana_keeps_a_login():
    env = _telemetry_services()["otel-lgtm"]["environment"]
    assert env["GF_AUTH_ANONYMOUS_ENABLED"] == "false"
    assert "GF_SECURITY_ADMIN_USER" in env and "GF_SECURITY_ADMIN_PASSWORD" in env
