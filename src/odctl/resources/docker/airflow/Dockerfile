FROM apache/airflow:3.3.0

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Custom Apache Airflow orchestrator image for the Open Data Stack. Fully loaded with pipeline execution providers for PostgreSQL, Trino, ClickHouse, Amazon S3, Flink, PySpark, and PyIceberg."

# Install Lean Open Data SDKs and Providers
# Pinned to the same Spark minor the spark image runs, because Iceberg
# publishes iceberg-spark-runtime per minor. Move it with that image, not on its
# own. See the renovate ceiling on apache/spark.
RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install \
    apache-airflow-providers-apache-flink==1.8.5 \
    apache-airflow-providers-amazon==9.31.0 \
    apache-airflow-providers-postgres==6.8.0 \
    apache-airflow-providers-trino==6.6.0 \
    clickhouse-connect==1.6.0 \
    'pyiceberg[s3]==0.11.1' \
    psycopg2-binary==2.9.12 \
    pyspark~=4.1.0 \
    'uvicorn>=0.31.0' \
    valkey==6.1.1

# Note: DAGs and Plugins are intentionally NOT copied here.
# They are managed at runtime via the SeaweedFS S3-sync sidecar.
