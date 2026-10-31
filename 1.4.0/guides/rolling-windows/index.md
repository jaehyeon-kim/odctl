# Rolling Windows in Flink SQL

A feature such as the sum of a card's payments over the last 10 minutes, 1 hour and 1 day needs one rolling window for each size. A rolling window, or `OVER` window in SQL, aggregates the rows of a key that fall within a time range before each new row. Flink SQL refuses two different `OVER` windows in one streaming query, so this guide shows the two ways around it. The end-to-end tests run the SQL below on every release.

This guide builds on [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/index.md), which opens the SQL client and writes to PostgreSQL over JDBC. It needs only `flink-lite`, which starts PostgreSQL through the catalog:

```bash
odctl up flink-lite
```

The endpoints are those of [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/index.md). Open the SQL client:

```bash
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
```

## One Query Cannot Hold Two Windows

Flink's documentation says that for streaming queries the `OVER` windows of all aggregates in one `SELECT` must be identical ([Over aggregation](https://github.com/apache/flink/blob/release-2.2/docs/content/docs/dev/table/sql/queries/over-agg.md), Flink 2.2). These statements declare 20 generated payments, one a minute for two cards, and ask for a 10-minute and a 1-hour sum in one query:

```sql
SET 'execution.runtime-mode' = 'streaming';
CREATE TABLE payments (card BIGINT, amount DOUBLE, seq BIGINT, ts AS TO_TIMESTAMP_LTZ(seq * 60000, 3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','fields.seq.kind'='sequence','fields.seq.start'='1','fields.seq.end'='20','fields.card.min'='1','fields.card.max'='2','fields.amount.min'='1','fields.amount.max'='10');
SELECT card,
  SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW) AS sum_10m,
  SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW) AS sum_1h
FROM payments;
```

The client prints `[ERROR] Could not execute SQL statement.` with this reason:

```text
org.apache.flink.table.api.TableException: Over Agg: Unsupported use of OVER windows. All aggregates must be computed on the same window. please re-check the over window statement.
```

## One Statement for Each Window Size

The first route is one statement for each window size, each writing its own table. This creates the two PostgreSQL tables:

```bash
docker exec postgres psql -U user -d odctl -c "
  CREATE TABLE card_sum_10m (card BIGINT, amount_sum DOUBLE PRECISION);
  CREATE TABLE card_sum_1h (card BIGINT, amount_sum DOUBLE PRECISION);"
```

Then run the two statements in a new SQL client session. The `sequence` field makes the source stop after 20 rows, and the event time `ts` makes each job write every row before it finishes. An `OVER` window on `PROCTIME()` would lose the rows still waiting for their timer when a bounded source ends:

```sql
SET 'execution.runtime-mode' = 'streaming';
SET 'table.dml-sync' = 'true';
CREATE TABLE payments (card BIGINT, amount DOUBLE, seq BIGINT, ts AS TO_TIMESTAMP_LTZ(seq * 60000, 3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','fields.seq.kind'='sequence','fields.seq.start'='1','fields.seq.end'='20','fields.card.min'='1','fields.card.max'='2','fields.amount.min'='1','fields.amount.max'='10');
CREATE TABLE sum_10m (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_10m','username'='user','password'='password');
CREATE TABLE sum_1h (card BIGINT, amount_sum DOUBLE) WITH ('connector'='jdbc','url'='jdbc:postgresql://postgres:5432/odctl','table-name'='card_sum_1h','username'='user','password'='password');
INSERT INTO sum_10m SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW) FROM payments;
INSERT INTO sum_1h SELECT card, SUM(amount) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW) FROM payments;
```

Each `INSERT` prints `[INFO] Complete execution of the SQL update statement.` once its job ends. This counts the rows of both tables:

```bash
docker exec postgres psql -U user -d odctl -c "
  SELECT (SELECT count(*) FROM card_sum_10m) AS rows_10m, (SELECT count(*) FROM card_sum_1h) AS rows_1h"
```

Each table holds 20 rows, one for each payment:

```text
 rows_10m | rows_1h
----------+---------
       20 |      20
(1 row)
```

The cost is one job for each window size, each reading the source again, and one table for each size that a reader has to join on the key. With four sizes that is four jobs.

## One Function for Every Size

The second route is one `KeyedProcessFunction` in the DataStream API, which keeps the events of the longest window in Flink state and computes every size from them. This sketch is not run by the end-to-end tests:

```python
from pyflink.common import Types
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import ListStateDescriptor

WINDOWS_MS = {"10m": 600_000, "1h": 3_600_000, "1d": 86_400_000, "7d": 604_800_000}


class RollingSums(KeyedProcessFunction):
    def open(self, runtime_context: RuntimeContext):
        # Every event of the longest window, for each key, kept in Flink state.
        self.events = runtime_context.get_list_state(
            ListStateDescriptor("events", Types.TUPLE([Types.LONG(), Types.DOUBLE()]))
        )

    def process_element(self, value, ctx):
        now = ctx.timestamp()
        kept = [(t, a) for t, a in self.events.get() if now - t <= WINDOWS_MS["7d"]]
        kept.append((now, value[1]))
        self.events.update(kept)
        yield value[0], {n: sum(a for t, a in kept if now - t <= ms) for n, ms in WINDOWS_MS.items()}
```

One job computes all sizes, but you write and test the code in Python or Java instead of SQL, and you manage the state, which grows with the events of the longest window for each key.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), the addresses are those of [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/#from-another-container): Flink's REST API is `http://jobmanager:8081` and PostgreSQL is `jdbc:postgresql://postgres:5432/odctl`.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It runs the first route with tables of its own for each run, so it can run again:

```bash
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
```

It prints `rows_10m` and `rows_1h` as `20` and `20`.
