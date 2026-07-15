FROM apache/airflow:3.2.1

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Custom Apache Airflow orchestrator image for the Open Data Stack. Fully loaded with pipeline execution providers for PostgreSQL, Trino, ClickHouse, Amazon S3, Flink, PySpark, and PyIceberg."

# Install Lean Open Data SDKs and Providers
# Pinning PySpark strictly to 4.0.x for Iceberg compatibility
RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install \
    apache-airflow-providers-apache-flink \
    apache-airflow-providers-amazon \
    apache-airflow-providers-postgres \
    apache-airflow-providers-trino \
    clickhouse-connect \
    'pyiceberg[s3]' \
    psycopg2-binary \
    pyspark~=4.1.0 \
    'uvicorn>=0.31.0' \
    valkey

# Note: DAGs and Plugins are intentionally NOT copied here.
# They are managed at runtime via the SeaweedFS S3-sync sidecar.
