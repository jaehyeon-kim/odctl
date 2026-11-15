#!/usr/bin/env bash
# Starts postgres, writes a second feature repository whose online store is
# PostgreSQL with pgvector, registers a feature view of three documents, writes
# their embeddings and retrieves the two nearest to a query vector. Run it in an
# environment with "feast[duckdb,postgres]==0.66.0" installed.
set -euo pipefail

odctl up postgres

mkdir -p vector_repo
cat > vector_repo/feature_store.yaml <<'YAML'
project: vector_demo
provider: local
registry:
  registry_type: sql
  path: postgresql+psycopg://user:password@127.0.0.1:5432/feast
offline_store:
  type: duckdb
online_store:
  type: postgres
  host: 127.0.0.1
  port: 5432
  database: vector
  user: user
  password: password
  sslmode: disable
  vector_enabled: true
entity_key_serialization_version: 3
YAML
cat > vector_repo/definitions.py <<'PY'
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
PY

feast -c vector_repo apply --skip-source-validation

python - <<'PY'
import datetime
import pandas as pd
from feast import FeatureStore

fs = FeatureStore(repo_path="vector_repo")
now = datetime.datetime.now(datetime.timezone.utc)
fs.write_to_online_store("docs", pd.DataFrame({
    "doc_id": [1, 2, 3],
    "title": ["Feast", "Flink", "Iceberg"],
    "embedding": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0]],
    "event_timestamp": [now] * 3,
}))

result = fs.retrieve_online_documents_v2(
    features=["docs:embedding", "docs:title"],
    query=[1.0, 0.0, 0.0],
    top_k=2,
    distance_metric="L2",
).to_dict()
print(result["title"])
PY
