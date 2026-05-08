#!/bin/bash
set -e

echo "Starting Unified Database Initialization"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Base Extensions and Permissions
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    GRANT pg_read_all_stats TO "$POSTGRES_USER";

    -- CDC Schema
    CREATE SCHEMA IF NOT EXISTS cdc;
    GRANT ALL ON SCHEMA cdc TO "$POSTGRES_USER";
    CREATE PUBLICATION cdc_pub FOR TABLES IN SCHEMA cdc;

    -- Dev Schema
    CREATE SCHEMA IF NOT EXISTS dev;
    GRANT ALL ON SCHEMA dev TO "$POSTGRES_USER";

    ALTER DATABASE "$POSTGRES_DB" SET search_path TO cdc, dev, public;

    -- Standardized Databases
    CREATE DATABASE marquez OWNER "$POSTGRES_USER";
    CREATE DATABASE omt OWNER "$POSTGRES_USER";
    CREATE DATABASE vector OWNER "$POSTGRES_USER";
    CREATE DATABASE iceberg OWNER "$POSTGRES_USER";

    -- MLOps & Analytics Databases
    CREATE DATABASE airflow OWNER "$POSTGRES_USER";
    CREATE DATABASE mlflow OWNER "$POSTGRES_USER";
    CREATE DATABASE metabase OWNER "$POSTGRES_USER";
EOSQL

# Loop through and add pg_stat_statements to all
for db in marquez omt vector iceberg airflow mlflow metabase; do
    echo "Configuring database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EOSQL
done

echo "Configuring vector extensions"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "vector" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "Unified Database Initialization Complete"
