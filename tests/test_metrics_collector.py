"""PostgreSQL and Valkey metrics come from otel-lgtm's own collector.

Neither exposes a Prometheus endpoint, and otel-lgtm's otelcol-contrib ships the
postgresql and redis receivers, so a second collector config adds them instead of
an exporter container. These checks pin that wiring. Nothing here needs Docker.
"""

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()


def _otel_lgtm():
    compose = yaml.safe_load((RESOURCES / "compose-obsv.yml").read_text())
    return compose["services"]["otel-lgtm"]


def _receivers_config():
    return yaml.safe_load((RESOURCES / "otelcol" / "odctl-receivers.yaml").read_text())


def test_receivers_config_is_mounted_and_passed_to_the_collector():
    service = _otel_lgtm()
    assert (
        "./otelcol/odctl-receivers.yaml:/otel-lgtm/odctl-receivers.yaml"
        in service["volumes"]
    )
    assert (
        service["environment"]["OTELCOL_EXTRA_ARGS"]
        == "--config=file:./odctl-receivers.yaml"
    )


def test_postgresql_and_valkey_are_scraped():
    receivers = _receivers_config()["receivers"]
    assert receivers["postgresql"]["endpoint"] == "postgres:5432"
    assert receivers["redis"]["endpoint"] == "valkey:6379"


def test_credentials_come_from_the_environment():
    receivers = _receivers_config()["receivers"]
    env = _otel_lgtm()["environment"]
    for value in (
        receivers["postgresql"]["username"],
        receivers["postgresql"]["password"],
        receivers["redis"]["username"],
        receivers["redis"]["password"],
    ):
        name = value.removeprefix("${env:").removesuffix("}")
        assert name in env, name


def test_the_image_pipeline_receivers_are_kept():
    # A merged list replaces the image's, so its own receivers must be repeated.
    receivers = _receivers_config()["service"]["pipelines"]["metrics"]["receivers"]
    assert receivers[:2] == ["otlp", "prometheus/collector"]
    assert {"postgresql", "redis"} <= set(receivers)
