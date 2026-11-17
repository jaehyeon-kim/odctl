# Commands from docs/guides/spark.md. .github/scripts/smoke.sh runs each section.

# --8<-- [start:run-sql]
docker exec spark-master /opt/spark/bin/spark-sql -e "
  CREATE NAMESPACE IF NOT EXISTS iceberg.demo;
  CREATE OR REPLACE TABLE iceberg.demo.t (id BIGINT) USING iceberg;
  INSERT INTO iceberg.demo.t VALUES (1),(2),(3);
  SELECT count(*) FROM iceberg.demo.t;"
# --8<-- [end:run-sql]

# --8<-- [start:event-logs]
docker exec spark-master ls /tmp/spark-events
# --8<-- [end:event-logs]
