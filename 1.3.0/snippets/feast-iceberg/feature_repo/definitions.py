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
