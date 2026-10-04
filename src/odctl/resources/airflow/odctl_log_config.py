"""Airflow logging config for odctl, loaded through [logging] logging_config_class.

Airflow pushes metrics to the telemetry profile over OTLP. When that profile is
not running, the OpenTelemetry exporter logs a retry and a failure for every
batch from every Airflow process. It logs through the standard logging module,
which [logging] namespace_levels does not reach, so its level is set here. When
telemetry is running, its smoke test checks that Airflow's series arrive.
"""

from copy import deepcopy

from airflow.config_templates.airflow_local_settings import DEFAULT_LOGGING_CONFIG

LOGGING_CONFIG = deepcopy(DEFAULT_LOGGING_CONFIG)
LOGGING_CONFIG["loggers"]["opentelemetry.exporter.otlp.proto.http.metric_exporter"] = {
    "level": "CRITICAL"
}
