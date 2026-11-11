# Vector Retrieval with Feast

Feast can return the stored rows whose embeddings are nearest to a query embedding, which is how a retrieval step finds the documents that match a question. An embedding is a list of numbers that represents a text, and the nearest embeddings belong to the most similar texts. This guide runs a second Feast repository, `vector_repo`, whose online store is PostgreSQL with pgvector, the extension that stores vectors and finds the nearest ones. Feast's `retrieve_online_documents_v2` is the call that returns them. The end-to-end tests run the steps below on every release.

This guide builds on [Feast with Iceberg](https://jaehyeon.me/odctl/latest/guides/feast-iceberg/index.md), which defines feature views and a feature repository, and on [Hybrid Search](https://jaehyeon.me/odctl/latest/guides/hybrid-search/index.md), which describes the `vector` database and its pgvector extension.

| Endpoint                              | Address                                                   |
| ------------------------------------- | --------------------------------------------------------- |
| PostgreSQL from the host              | `127.0.0.1:5432`, user `user`, password `password`        |
| PostgreSQL inside the `odctl` network | `postgres:5432`                                           |
| Database for the vectors              | `vector`                                                  |
| Registry                              | the `feast` database on PostgreSQL, project `vector_demo` |

Start PostgreSQL and install the client, with the extras that read DuckDB and PostgreSQL:

```bash
odctl up postgres
pip install "feast[duckdb,postgres]==0.66.0"
```

## Define a Second Repository

A feature repository has one online store. The default repository of the `feast` profile uses Feast's Redis online store for Valkey, and that store has no document retrieval method. Vectors therefore go in a second repository whose online store is PostgreSQL.

The `valkey` profile also has a 512 MB memory limit, set by `mem_limit` of `valkey` in `.odctl/compose-store.yml`, so the vectors of a large corpus belong in PostgreSQL too.

Save this file as `vector_repo/feature_store.yaml`. `vector_enabled: true` makes the online store keep vectors in pgvector columns. `sslmode: disable` is needed because Feast asks for SSL by default and odctl's PostgreSQL does not serve it:

```yaml
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
```

Save the definitions as `vector_repo/definitions.py`. They declare the entity `doc` and the feature view `docs`. The field `embedding` holds three numbers, as in Hybrid Search, and `vector_index=True` marks it as the field to search:

```python
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
```

Run this from the folder that holds `vector_repo`. `apply` writes the definitions to the registry and creates the table for `docs` in the `vector` database. `--skip-source-validation` stops Feast from looking for the file behind the batch source:

```bash
feast -c vector_repo apply --skip-source-validation
```

`apply` prints `Applying changes for project vector_demo` and `Deploying infrastructure for docs`.

## Write and Retrieve

Save this code as `write.py` and run it with `python write.py` in the same folder. It writes three documents to the online store, each with its embedding. The `event_timestamp` column is required, and a second run replaces the three rows:

```python
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
```

Then save this code as `retrieve.py` and run it with `python retrieve.py`. It asks for the two documents nearest to `[1, 0, 0]` by Euclidean distance (`L2`):

```python
from feast import FeatureStore

fs = FeatureStore(repo_path="vector_repo")
result = fs.retrieve_online_documents_v2(
    features=["docs:embedding", "docs:title"],
    query=[1.0, 0.0, 0.0],
    top_k=2,
    distance_metric="L2",
).to_dict()
print(result["title"])
```

It prints `['Feast', 'Iceberg']`. The query is `[1, 0, 0]`, the same vector as `Feast`. `Iceberg` at `[0.9, 0.1, 0]` is the next nearest. `Flink` at `[0, 1, 0]` is the farthest, and `top_k=2` leaves it out.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), a repository for the services sets `host: postgres` in `online_store` and uses `postgres:5432` in the registry path, with the same user and password.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace, in an environment with the client installed as above. It writes the repository files into `vector_repo` in that folder. A second run registers the same definitions again and replaces the three rows:

```bash
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
```

It prints the lines of `apply` and then `['Feast', 'Iceberg']`.
