#!/usr/bin/env bash
# Starts fluss and flink-lite, then writes three rows to a Fluss table with
# Flink SQL and reads them back. Each run uses its own table name.
set -euo pipefail

odctl up fluss flink-lite

# The tablet server registers in ZooKeeper a few seconds after it starts.
until docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids 2>/dev/null | grep '^\[0' >/dev/null; do
  sleep 2
done

run=$(date +%s)
docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<SQL | grep -E '^[|+]|ERROR'
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG fluss_catalog WITH ('type' = 'fluss', 'bootstrap.servers' = 'fluss-coordinator:9123');
CREATE DATABASE IF NOT EXISTS fluss_catalog.demo;
CREATE TABLE fluss_catalog.demo.t_$run (id BIGINT, name STRING, PRIMARY KEY (id) NOT ENFORCED);
INSERT INTO fluss_catalog.demo.t_$run VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT * FROM fluss_catalog.demo.t_$run LIMIT 10;
SQL
