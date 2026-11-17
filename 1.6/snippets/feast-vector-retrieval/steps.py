# --8<-- [start:write]
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
# --8<-- [end:write]

# --8<-- [start:retrieve]
from feast import FeatureStore

fs = FeatureStore(repo_path="vector_repo")
result = fs.retrieve_online_documents_v2(
    features=["docs:embedding", "docs:title"],
    query=[1.0, 0.0, 0.0],
    top_k=2,
    distance_metric="L2",
).to_dict()
print(result["title"])
# --8<-- [end:retrieve]
