-- Flink SQL from docs/guides/iceberg-ingestion.md, run by .github/scripts/smoke.sh
-- through the SQL client.

-- --8<-- [start:flink]
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG ice WITH ('type'='iceberg','catalog-type'='rest','uri'='http://catalog:8181','warehouse'='s3://warehouse','s3.endpoint'='http://seaweed:8333','s3.path-style-access'='true','s3.access-key-id'='user','s3.secret-access-key'='password');
CREATE DATABASE IF NOT EXISTS ice.demo_flink;
CREATE TABLE ice.demo_flink.t (id BIGINT, name STRING);
INSERT INTO ice.demo_flink.t VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT COUNT(*) FROM ice.demo_flink.t;
-- --8<-- [end:flink]
