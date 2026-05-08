FROM apache/airflow:3.2.1

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
    pyspark~=4.0.0

# Install Feast separately to bypass the pip backtracking trap
RUN pip install --no-cache-dir 'feast[clickhouse,redis,aws,postgres]'

# Note: DAGs and Plugins are intentionally NOT copied here.
# They are managed at runtime via the SeaweedFS S3-sync sidecar.
