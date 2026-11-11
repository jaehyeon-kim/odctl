-- Flink SQL from docs/guides/fluss.md, run by .github/scripts/smoke.sh through
-- the SQL client.

-- --8<-- [start:table]
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG fluss_catalog WITH ('type' = 'fluss', 'bootstrap.servers' = 'fluss-coordinator:9123');
CREATE DATABASE IF NOT EXISTS fluss_catalog.demo;
CREATE TABLE fluss_catalog.demo.t (id BIGINT, name STRING, PRIMARY KEY (id) NOT ENFORCED);
INSERT INTO fluss_catalog.demo.t VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT * FROM fluss_catalog.demo.t LIMIT 10;
-- --8<-- [end:table]
