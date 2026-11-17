# Commands from docs/guides/flink-sql.md. .github/scripts/smoke.sh runs each
# section; the SQL client reads steps.sql there instead of a terminal.

# --8<-- [start:create-topic-table]
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
  --create --if-not-exists --topic orders --partitions 1 --replication-factor 1

docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE supplier_stats (supplier TEXT PRIMARY KEY, orders BIGINT, total DOUBLE PRECISION);"
# --8<-- [end:create-topic-table]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]

# --8<-- [start:check]
docker exec postgres psql -U user -d odctl -c "SELECT * FROM supplier_stats ORDER BY supplier"
# --8<-- [end:check]
