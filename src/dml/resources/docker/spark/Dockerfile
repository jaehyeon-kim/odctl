FROM apache/spark:4.0.2

# Switch to root to install system-wide packages
USER root

# Only install libraries required for distributed UDFs
RUN pip install --no-cache-dir \
    'feast[clickhouse,redis,aws,postgres]' \
    'mlflow~=3.12.0' \
    'boto3'

# Revert to the official Apache Spark non-root user ID
USER 185
