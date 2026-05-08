FROM quay.io/jupyter/scipy-notebook:python-3.13

# Install Open DataML Stack SDKs
RUN pip install --no-cache-dir \
    'pyspark~=4.0.0' \
    'kafka-python>=2.0.2' \
    'confluent-kafka>=2.0.0' \
    'dataclasses-avroschema[pydantic]' \
    'pyiceberg[s3]>=0.8.0' \
    'feast[redis,aws,spark,postgres,clickhouse]' \
    'mlflow~=3.12.0' \
    'clickhouse-connect' \
    'psycopg2-binary' \
    'trino' \
    'boto3'
