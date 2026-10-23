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

# --8<-- [start:feast-apply]
docker cp definitions.py feast-serve:/tmp/feature_repo/definitions.py
docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation
# --8<-- [end:feast-apply]

# --8<-- [start:feast-read]
curl -s -X POST http://127.0.0.1:6566/get-online-features \
  -H 'Content-Type: application/json' \
  -d '{"features": ["driver_stats:conv_rate"], "entities": {"driver_id": [1001]}}'
# --8<-- [end:feast-read]

# --8<-- [start:create-window-tables]
docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE card_sum_10m (card BIGINT, amount_sum DOUBLE PRECISION);
  CREATE TABLE card_sum_1h (card BIGINT, amount_sum DOUBLE PRECISION);"
# --8<-- [end:create-window-tables]

# --8<-- [start:check-windows]
docker exec postgres psql -U user -d odctl -c "
  SELECT (SELECT count(*) FROM card_sum_10m) AS rows_10m, (SELECT count(*) FROM card_sum_1h) AS rows_1h"
# --8<-- [end:check-windows]
