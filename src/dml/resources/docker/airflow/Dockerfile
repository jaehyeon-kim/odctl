FROM apache/airflow:3.2.1

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/open-dataml-stack"
LABEL org.opencontainers.image.description="Custom Apache Airflow orchestrator image for the Open DataML Stack. Fully loaded with pipeline execution providers for PostgreSQL, Trino, ClickHouse, Amazon S3, Flink, PySpark, PyIceberg, and Feast feature store integrations."

# Install Lean DataML SDKs and Providers
# Pinning PySpark strictly to 4.0.x for Iceberg compatibility
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-flink \
    apache-airflow-providers-amazon \
    apache-airflow-providers-postgres \
    apache-airflow-providers-trino \
    clickhouse-connect \
    'pyiceberg[s3]' \
    psycopg2-binary \
    pyspark~=4.1.0 \
    'uvicorn>=0.31.0'

# Install Feast separately to bypass the pip backtracking trap
RUN pip install --no-cache-dir 'feast[clickhouse,redis,aws,postgres]'

# Note: DAGs and Plugins are intentionally NOT copied here.
# They are managed at runtime via the SeaweedFS S3-sync sidecar.
