# Pinned to the 4.1 series on purpose. Iceberg 1.11.0 publishes
# iceberg-spark-runtime for 4.0 and 4.1 only, so a 4.2 image loads a runtime
# built against 4.1 and every Iceberg statement dies with
# IncompatibleClassChangeError on connector.catalog.View. HADOOP_AWS_V in
# versions.env is also matched to the Hadoop this series bundles, and the
# airflow image pins pyspark to the same minor. Raise all four together, and
# only once Iceberg ships a runtime for the newer minor. See PR #29.
FROM apache/spark:4.1.3

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
