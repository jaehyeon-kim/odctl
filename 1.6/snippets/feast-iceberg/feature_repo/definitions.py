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
