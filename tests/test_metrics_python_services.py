"""Metrics settings for Spark, MLflow, Feast and Airflow.

Each service exposes metrics to the telemetry profile without an extra container:
Spark through its PrometheusServlet sink, MLflow and Feast through their own
Prometheus endpoints, and Airflow by pushing OTLP to the telemetry collector.
These checks pin the settings in the compose files. Nothing here needs Docker.
"""

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()


def _services(name):
    return yaml.safe_load((RESOURCES / name).read_text())["services"]


def test_spark_mounts_the_prometheus_servlet_config():
    for name, service in _services("compose-spark.yml").items():
        assert (
            "./spark/metrics.properties:/opt/spark/conf/metrics.properties:ro"
            in service["volumes"]
        ), name
    config = (RESOURCES / "spark" / "metrics.properties").read_text()
    assert (
        "*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet"
        in config
    )
    assert "master.sink.prometheusServlet.path=/metrics/master/prometheus" in config
    assert (
        "applications.sink.prometheusServlet.path=/metrics/applications/prometheus"
        in config
    )


def test_mlflow_exposes_prometheus_metrics():
    assert "--expose-prometheus" in _services("compose-mlops.yml")["mlflow"]["command"]


def test_feast_serve_enables_its_metrics_server():
    assert "--metrics" in _services("compose-mlops.yml")["feast-serve"]["command"]


def test_airflow_pushes_otlp_to_the_telemetry_collector():
    env = _services("compose-orch.yml")["airflow"]["environment"]
    assert env["AIRFLOW__METRICS__OTEL_ON"] == "True"
    assert env["AIRFLOW__METRICS__OTEL_HOST"] == "otel-lgtm"
    assert env["AIRFLOW__METRICS__OTEL_PORT"] == "4318"
