#!/usr/bin/env bash
# Starts flink-lite, computes a 10-minute and a 1-hour rolling sum over 20
# generated payments, one Flink SQL statement for each window size, and prints
# how many rows each wrote to PostgreSQL. Each run uses its own table names.
set -euo pipefail

odctl up flink-lite

run=$(date +%s)
docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE card_sum_10m_$run (card BIGINT, amount_sum DOUBLE PRECISION);
  CREATE TABLE card_sum_1h_$run (card BIGINT, amount_sum DOUBLE PRECISION);"

docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<SQL | grep -E 'ERROR|Exception' || true
SET 'execution.runtime-mode' = 'streaming';
SET 'table.dml-sync' = 'true';
CREATE TABLE payments (card BIGINT, amount DOUBLE, seq BIGINT, ts AS TO_TIMESTAMP_LTZ(seq * 60000, 3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','fields.seq.kind'='sequence','fields.seq.start'='1','fields.seq.end'='20','fields.card.min'='1','fields.card.max'='2','fields.amount.min'='1','fields.amount.max'='10');
CREATE TABLE sum_10m (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_10m_$run','username'='user','password'='password');
CREATE TABLE sum_1h (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_1h_$run','username'='user','password'='password');
INSERT INTO sum_10m SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW) FROM payments;
INSERT INTO sum_1h SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW) FROM payments;
SQL

docker exec postgres psql -U user -d odctl -c "
  SELECT (SELECT count(*) FROM card_sum_10m_$run) AS rows_10m, (SELECT count(*) FROM card_sum_1h_$run) AS rows_1h"
