"""Grafana dashboards provisioned into the telemetry profile.

Each service's dashboard loads from grafana/dashboards/ through Grafana's
provisioning directory in grafana/otel-lgtm, and grafana/sources.yml records
where each one came from and what it covers. These checks pin the mount, the
coverage of every metrics source and the data source every query uses. Nothing
here needs Docker.
"""

import json

import yaml

from odctl.config import get_internal_resources_dir

RES = get_internal_resources_dir()
GRAFANA = RES / "grafana"
PROVISIONING = "/otel-lgtm/grafana/conf/provisioning/dashboards"
# The Prometheus data source the image provisions in grafana-datasources.yaml.
PROMETHEUS = {"type": "prometheus", "uid": "prometheus"}
# Grafana's built-in source for annotations, which needs no data source.
BUILTIN = {"type": "grafana", "uid": "-- Grafana --"}


def _sources():
    return yaml.safe_load((GRAFANA / "sources.yml").read_text())


def _dashboards():
    return {
        path.name: json.loads(path.read_text())
        for path in sorted((GRAFANA / "dashboards").glob("*.json"))
    }


def _datasources(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "datasource":
                yield value
            else:
                yield from _datasources(value)
    elif isinstance(node, list):
        for item in node:
            yield from _datasources(item)


def test_dashboards_are_mounted_into_the_provisioning_directory():
    compose = yaml.safe_load((RES / "compose-obsv.yml").read_text())
    volumes = compose["services"]["otel-lgtm"]["volumes"]
    assert f"./grafana/odctl-dashboards.yaml:{PROVISIONING}/odctl.yaml:ro" in volumes
    assert f"./grafana/dashboards:{PROVISIONING}/odctl:ro" in volumes
    provider = yaml.safe_load((GRAFANA / "odctl-dashboards.yaml").read_text())
    [odctl] = provider["providers"]
    assert odctl["type"] == "file"
    assert odctl["options"]["path"] == f"{PROVISIONING}/odctl"


def test_every_scrape_job_has_a_dashboard_or_is_listed_without_one():
    config = yaml.safe_load((RES / "prometheus" / "prometheus.yml").read_text())
    jobs = {job["job_name"] for job in config["scrape_configs"]}
    sources = _sources()
    covered = [
        job for entry in sources["dashboards"].values() for job in entry.get("jobs", [])
    ]
    assert len(covered) == len(set(covered)), "a job is covered twice"
    without = set(sources["no_dashboard"])
    assert not set(covered) & without
    assert set(covered) | without == jobs


def test_collector_and_pushed_metrics_have_dashboards():
    receivers = yaml.safe_load((RES / "otelcol" / "odctl-receivers.yaml").read_text())[
        "receivers"
    ]
    entries = _sources()["dashboards"].values()
    covered = {r for entry in entries for r in entry.get("receivers", [])}
    assert covered == set(receivers)
    assert {s for entry in entries for s in entry.get("otlp", [])} == {"airflow"}


def test_every_dashboard_file_is_indexed_with_its_source():
    sources = _sources()["dashboards"]
    assert set(sources) == set(_dashboards())
    for name, entry in sources.items():
        if entry["source"] == "grafana.com":
            assert isinstance(entry["id"], int), name
            assert isinstance(entry["revision"], int), name
        else:
            assert entry["source"], name


def test_dashboards_query_only_the_provisioned_prometheus():
    uids = set()
    for name, dashboard in _dashboards().items():
        uids.add(dashboard["uid"])
        datasources = list(_datasources(dashboard))
        assert datasources, name
        for ds in datasources:
            assert ds in (PROMETHEUS, BUILTIN), (name, ds)
        variables = dashboard.get("templating", {}).get("list", [])
        assert all(v.get("type") != "datasource" for v in variables), name
        text = json.dumps(dashboard)
        assert "${DS_" not in text and "__inputs" not in dashboard, name
    assert len(uids) == len(_dashboards()), "two dashboards share a uid"
