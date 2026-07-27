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

# Pre-create the event log directory owned by the spark user. A named volume
# mounted here inherits this ownership, so spark-submit can write its logs.
RUN mkdir -p /tmp/spark-events && chown 185:185 /tmp/spark-events

# Revert to the official Apache Spark non-root user ID
USER 185
