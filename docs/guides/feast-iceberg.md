# Feast with Iceberg

The `feast` profile runs the Feast UI and the online feature server. Feast stores no feature values of its own. Feature definitions live in a SQL registry in PostgreSQL, offline values come from Iceberg tables through the REST catalog, and online values are served from Valkey. You run `feast apply` and the other client commands from your own environment. The steps below come from the end-to-end tests.

```bash
odctl up feast
pip install "feast[duckdb,iceberg,redis,postgres]==0.66.0" pyarrow
```

## Point the clients at the stack

PyIceberg, which Feast uses to read Iceberg, takes its catalog settings from the environment:

```bash
export PYICEBERG_CATALOG__ODCTL__TYPE=rest
export PYICEBERG_CATALOG__ODCTL__URI=http://127.0.0.1:8181
export PYICEBERG_CATALOG__ODCTL__WAREHOUSE=s3://warehouse/
export PYICEBERG_CATALOG__ODCTL__S3__ENDPOINT=http://127.0.0.1:8333
export PYICEBERG_CATALOG__ODCTL__S3__ACCESS_KEY_ID=user
export PYICEBERG_CATALOG__ODCTL__S3__SECRET_ACCESS_KEY=password
export PYICEBERG_CATALOG__ODCTL__S3__PATH_STYLE_ACCESS=true
export PYICEBERG_CATALOG__ODCTL__S3__REGION=us-east-1
```

## Create an Iceberg table

```python
import datetime, pyarrow as pa
from pyiceberg.catalog import load_catalog

cat = load_catalog("odctl")
cat.create_namespace_if_not_exists("demo")
schema = pa.schema([
    pa.field("driver_id", pa.int64(), nullable=False),
    pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("conv_rate", pa.float32(), nullable=False),
])
t = cat.create_table("demo.driver_stats", schema=schema)
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
t.append(pa.Table.from_pydict({
    "driver_id": [1001, 1002],
    "event_timestamp": [now - datetime.timedelta(hours=1)] * 2,
    "conv_rate": [0.5, 0.75],
}, schema=schema))
```

## Define the feature repository

`feature_repo/feature_store.yaml`:

```yaml
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
```

`feature_repo/definitions.py`:

```python
from datetime import timedelta
from feast import Entity, FeatureView, Field
from feast.types import Float32
from feast.infra.data_sources.contrib.iceberg_catalog.iceberg_source import IcebergSource

driver = Entity(name="driver", join_keys=["driver_id"])
src = IcebergSource(
    warehouse="", namespace="demo", table="driver_stats",
    catalog_type="rest", catalog_name="odctl",
    endpoint="http://127.0.0.1:8181",
    timestamp_field="event_timestamp",
)
fv = FeatureView(
    name="driver_stats", entities=[driver], ttl=timedelta(days=365),
    schema=[Field(name="conv_rate", dtype=Float32)], source=src, online=True,
)
```

Pass `warehouse=""` and `catalog_name="odctl"`. Feast's REST client puts the warehouse into the URL path, and the catalog serves its API with no prefix, so a real warehouse value fails with HTTP 400.

## Register and materialise

```bash
feast -c feature_repo apply
feast -c feature_repo materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"
```

`FeatureStore(repo_path="feature_repo").get_historical_features(...)` now takes a point-in-time join from Iceberg through DuckDB, and `get_online_features(...)` reads the materialised values from Valkey.

## Serve from the stack

The UI at `http://127.0.0.1:8890` and the online feature server at `http://127.0.0.1:6566` load their repository from `s3://feast/repo`. To serve your features, upload the repository there with container addresses in its `feature_store.yaml`: `postgres:5432`, `valkey:6379` and `http://catalog:8181`. The services check that prefix every 15 seconds and restart Feast when it changes.

Once the repository is uploaded, the UI lists the project and its feature views:

![Feast UI showing the driver_stats feature view](../images/feast-ui.png){ .screenshot }
