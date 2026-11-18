#!/usr/bin/env bash
# Copies the prepared Python of this suite into the run's workspace, then points its
# scripts at the copy. `make_suite.py` writes the prepared copy's path into python-path,
# beside the case folders; claude plugin eval runs this script by its full path, from
# the workspace, before the sandbox starts.
set -eu
prepared=$(cat "$(dirname "$0")/../python-path")
cp -R "$prepared" py
# Why: the path is matched and replaced as literal text, so a character such as [ in it
# cannot act as a pattern; perl reads both paths from the environment, so the single
# quotes are meant
# shellcheck disable=SC2016
grep -lF "$prepared/" py/bin/* | PREP="$prepared/" NEW="$PWD/py/" xargs perl -pi -e 's/\Q$ENV{PREP}\E/$ENV{NEW}/g'
# The request names the feature repository the user already applied from the laptop,
# as the Feast with Iceberg guide writes it (docs/snippets/feast-iceberg/feature_repo/).
mkdir -p feature_repo
cat > feature_repo/feature_store.yaml <<'YAML'
project: demo
provider: local
registry:
  registry_type: sql
  path: postgresql+psycopg://user:password@127.0.0.1:5432/feast
offline_store:
  type: duckdb
online_store:
  type: redis
  connection_string: "127.0.0.1:6379,username=user,password=password"
entity_key_serialization_version: 3
YAML
cat > feature_repo/definitions.py <<'PY'
from datetime import timedelta
from feast import Entity, FeatureView, Field
from feast.types import Float32
from feast.value_type import ValueType
from feast.infra.data_sources.contrib.iceberg_catalog.iceberg_source import IcebergSource

driver = Entity(name="driver", join_keys=["driver_id"], value_type=ValueType.INT64)
src = IcebergSource(
    warehouse="", namespace="demo", table="driver_stats",
    catalog_type="rest", catalog_name="odctl",
    timestamp_field="event_timestamp",
)
fv = FeatureView(
    name="driver_stats", entities=[driver], ttl=timedelta(days=365),
    schema=[Field(name="conv_rate", dtype=Float32)], source=src, online=True,
)
PY
