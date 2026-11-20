-- Flink SQL from docs/guides/rolling-windows.md, run by .github/scripts/smoke.sh
-- through the SQL client.

-- --8<-- [start:windows-refused]
SET 'execution.runtime-mode' = 'streaming';
CREATE TABLE payments (card BIGINT, amount DOUBLE, seq BIGINT, ts AS TO_TIMESTAMP_LTZ(seq * 60000, 3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','fields.seq.kind'='sequence','fields.seq.start'='1','fields.seq.end'='20','fields.card.min'='1','fields.card.max'='2','fields.amount.min'='1','fields.amount.max'='10');
SELECT card,
  SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW) AS sum_10m,
  SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW) AS sum_1h
FROM payments;
-- --8<-- [end:windows-refused]

-- --8<-- [start:windows-one-per-size]
SET 'execution.runtime-mode' = 'streaming';
SET 'table.dml-sync' = 'true';
CREATE TABLE payments (card BIGINT, amount DOUBLE, seq BIGINT, ts AS TO_TIMESTAMP_LTZ(seq * 60000, 3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','fields.seq.kind'='sequence','fields.seq.start'='1','fields.seq.end'='20','fields.card.min'='1','fields.card.max'='2','fields.amount.min'='1','fields.amount.max'='10');
CREATE TABLE sum_10m (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_10m','username'='user','password'='password');
CREATE TABLE sum_1h (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_1h','username'='user','password'='password');
INSERT INTO sum_10m SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW) FROM payments;
INSERT INTO sum_1h SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW) FROM payments;
-- --8<-- [end:windows-one-per-size]
