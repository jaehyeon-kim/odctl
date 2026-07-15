FROM apache/spark:4.1.2

# Switch to root to install system-wide packages
USER root

# Only install libraries required for distributed UDFs
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    'clickhouse-connect' \
    'psycopg2-binary' \
    'valkey' \
    'mlflow~=3.12.0' \
    'boto3'

# Revert to the official Apache Spark non-root user ID
USER 185
