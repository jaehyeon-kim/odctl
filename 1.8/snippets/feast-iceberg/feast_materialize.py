from datetime import datetime, timezone

from airflow.sdk import dag, task


@dag(
    dag_id="feast_materialize",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule="@hourly",
    catchup=False,
)
def feast_materialize():
    """Copy the latest feature values to Valkey every hour."""

    @task
    def materialize():
        """Materialise the feature views up to now."""
        # Imported here so that parsing the file does not load Feast.
        import os

        from feast import FeatureStore, RepoConfig

        store = FeatureStore(config=RepoConfig(
            project="demo",
            provider="local",
            registry={"registry_type": "sql", "path": os.environ["FEAST_REGISTRY"]},
            offline_store={"type": "duckdb"},
            online_store={
                "type": "redis",
                "connection_string": "valkey:6379,username=user,password=password",
            },
            entity_key_serialization_version=3,
        ))
        store.materialize_incremental(end_date=datetime.now(timezone.utc))

    materialize()


feast_materialize()
