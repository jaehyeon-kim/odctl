FROM apache/airflow:3.3.2

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Custom Apache Airflow orchestrator image for the Open Data Stack. Fully loaded with pipeline execution providers for PostgreSQL, Trino, ClickHouse, Amazon S3, Flink, PySpark, and PyIceberg, the MLflow and Feast clients, and the XGBoost, LightGBM and PyTorch runtimes."

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
    'pyiceberg[s3]==0.12.0' \
    psycopg2-binary==2.9.12 \
    pyspark~=4.1.0 \
    'uvicorn>=0.31.0' \
    valkey==6.1.1

# Clients for the stack's own MLflow and Feast services, matched to their servers:
# the mlflow image runs 3.16 and the feast profile runs feature-server 0.66.0.
# Feast's offline half runs in the task's process, so it needs the DuckDB,
# Iceberg, Postgres registry and Valkey extras here rather than in a server.
RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install \
    'mlflow~=3.16.0' \
    'feast[duckdb,iceberg,postgres,redis]==0.66.0'

# Model runtimes, pinned to the same minors as the mlops image, because a model
# trained here is loaded there. A model saved by a newer runtime is not
# guaranteed to load in an older one. Raise both images together. XGBoost is held
# at 3.2 by the mlops image, whose Python 3.11 cannot install 3.3 or later.
RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install \
    'xgboost~=3.2.0' \
    'lightgbm~=4.7.0'

# CPU torch from PyTorch's own index, since PyPI ships the CUDA build.
RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install 'torch~=2.14.0' --index-url https://download.pytorch.org/whl/cpu

# Note: DAGs and Plugins are intentionally NOT copied here.
# They are managed at runtime via the SeaweedFS S3-sync sidecar.
