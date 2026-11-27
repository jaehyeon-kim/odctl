# Commands from docs/guides/rolling-windows.md. .github/scripts/smoke.sh runs each
# section; the SQL client reads steps.sql there instead of a terminal.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up flink-lite
# --8<-- [end:up]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]

# --8<-- [start:create-window-tables]
docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE card_sum_10m (card BIGINT, amount_sum DOUBLE PRECISION);
  CREATE TABLE card_sum_1h (card BIGINT, amount_sum DOUBLE PRECISION);"
# --8<-- [end:create-window-tables]

# --8<-- [start:check-windows]
docker exec postgres psql -U user -d odctl -c "
  SELECT (SELECT count(*) FROM card_sum_10m) AS rows_10m, (SELECT count(*) FROM card_sum_1h) AS rows_1h"
# --8<-- [end:check-windows]
