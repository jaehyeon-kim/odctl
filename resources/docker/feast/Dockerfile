FROM python:3.13-slim

WORKDIR /opt/feast/feature_repo

RUN pip install --no-cache-dir \
    'feast[clickhouse,redis,aws,postgres]' \
    clickhouse-connect \
    psycopg2-binary
