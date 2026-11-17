# Python from docs/guides/feast-iceberg.md, run by .github/scripts/smoke.sh with
# the catalog settings from commands.sh in the environment.

# --8<-- [start:create-table]
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
# --8<-- [end:create-table]

# --8<-- [start:read]
from feast import FeatureStore

fs = FeatureStore(repo_path="feature_repo")
print(fs.get_online_features(
    features=["driver_stats:conv_rate"],
    entity_rows=[{"driver_id": 1001}, {"driver_id": 1002}],
).to_dict())
# --8<-- [end:read]
