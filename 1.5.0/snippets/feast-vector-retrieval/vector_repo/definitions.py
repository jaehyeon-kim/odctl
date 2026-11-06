from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Array, Float32, String
from feast.value_type import ValueType

doc = Entity(name="doc", join_keys=["doc_id"], value_type=ValueType.INT64)
# Nothing reads this file. A feature view needs a batch source, and the rows go
# straight to the online store.
batch = FileSource(path="/tmp/docs.parquet", timestamp_field="event_timestamp")
docs = FeatureView(
    name="docs",
    entities=[doc],
    ttl=timedelta(days=365),
    schema=[
        Field(name="embedding", dtype=Array(Float32), vector_index=True, vector_length=3),
        Field(name="title", dtype=String),
    ],
    source=batch,
    online=True,
)
