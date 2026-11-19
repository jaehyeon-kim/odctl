# ch-distributed-count

Answer sheet of the case `ch-distributed-count`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A6 (service behaviour stated without a run or its source), A10 (a check that cannot fail), A3 (address from the wrong side), A12 (a number given with no reason).

## Records

- planning `architecting-analytics/validation-live-stack.md:143`: ClickHouse's insert behaviour made insert-then-read racy (A6, A8).
- planning `odctl/release/1.8.0/review-batch2-round1.md:9` (S3): a query's result reasoned from memory (A6).
- planning `architecting-analytics/validation-live-stack.md:153`: a check that did not read the data it was about (A10).
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the wrong side (A3).
- A12 extends the evidence of `planning/odctl/plan-agent-skill.md:30`.

## Right answer

- From the host: HTTP `http://127.0.0.1:8123` (`ch-11`), and `8124` to `8126` for the other servers (`registry.yml:186`; `docs/guides/clickhouse.md:13`); login `default` or `user` with password `password` (`clickhouse/users.xml:29-48`), for example `curl --user default:password --data-binary "<query>" http://127.0.0.1:8123/`.
- On `ch-full`, `{cluster}` is `odctl_cluster`, two shards of two replicas (`clickhouse/macros-11.xml`; `clickhouse/config.xml:33-45`; `docs/guides/clickhouse.md:42`). The local table: `CREATE TABLE ... ON CLUSTER '{cluster}' (...) ENGINE = ReplicatedMergeTree ORDER BY ...` (`docs/snippets/clickhouse/commands.sh:23-24`). Over it, a `Distributed('odctl_cluster', <db>, <local table>, <sharding key>)` table, created `ON CLUSTER` or at least on the server the script queries.
- Insert through the Distributed table. By default it sends the rows to the shards in the background (`distributed_foreground_insert` is false, ClickHouse tag `v25.12.9.61-stable`, `src/Core/Settings.cpp:734-737`; the image is `clickhouse-server:25.12-alpine`, `compose-analytics.yml:4`), so a count straight after the insert can be below 10000. Right: `SETTINGS distributed_foreground_insert = 1` on the insert, `SYSTEM FLUSH DISTRIBUTED <table>` before the count, or a repeated count with a limit and its reason.
- Count through the Distributed table: one server's local table holds only its shard's rows (`docs/guides/clickhouse.md:56`; `smoke.sh:485`). The script exits 1 unless the count is exactly 10000, and also when curl fails (`curl -f`, or `set -e` with a check of the answer).
- A rerun of the script on the same stack: a fixed table name with `IF NOT EXISTS` loads the numbers twice and the count is 20000, so the script fails on a second run; a name unique to the run, or a drop first, avoids that. Not counted: it is not one of this case's kinds.

## Wrong answers seen or expected

- A6: counting straight after a background insert, with a statement that the insert is synchronous; counting one server's local table and stating that it holds all rows.
- A10: a script that prints the count and exits 0 whatever it is; `curl` without `-f` and no check of the answer, so an error text compared loosely passes.
- A3: `http://ch-11:8123` or `clickhouse:8123` from the laptop; a login other than `default` or `user` with `password`.
- A12: a retry limit or `sleep` with no reason.
