# fluss-latest-price

Answer sheet of the case `fluss-latest-price`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A6 (service behaviour stated without a run or its source), A10 (a check that cannot fail), A2 (service called before it is ready), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:7` (S3) and `odctl/release/1.8.0/review-batch2-round1.md:9` (S3): how a service keeps or drops rows described from memory (A6).
- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1) and `odctl/release/1.4.0/audit.md:11` (M1): checks that could not fail (A10).
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit (A2).

## Right answer

- `odctl up fluss flink-lite` (`docs/snippets/fluss/commands.sh:7`).
- The SQL runs in the JobManager container: `docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh < latest_price.sql` (`docs/guides/fluss.md:89`), or `docker cp` and `-f`. Each client run is a new session, so each file that names the catalog creates it.
- Catalog: `CREATE CATALOG fluss_catalog WITH ('type' = 'fluss', 'bootstrap.servers' = 'fluss-coordinator:9123')` (`docs/snippets/fluss/steps.sql:8`; `docs/guides/fluss.md:69`), then `CREATE DATABASE IF NOT EXISTS fluss_catalog.shop` and the table with `PRIMARY KEY (product_id) NOT ENFORCED`.
- A Fluss primary-key table keeps only the last row written for each key: its default merge engine is LastRow, "only the last entry will be retained" (fluss.apache.org, Primary Key Table, version 1.0; the image is `apache/fluss:1.0.0`, `compose-store.yml:29`). So the updates are inserted as they come, in order, and no SQL picks the latest; a table with no primary key keeps all five rows. Rows of one `INSERT ... VALUES` keep their order through the one source task: inferred, not confirmed by a run; one `INSERT` per update, with `table.dml-sync`, keeps the order for certain.
- `SET 'execution.runtime-mode' = 'batch'` and `SET 'table.dml-sync' = 'true'` (`steps.sql:5-6`), so the writes have finished before the check reads; Fluss 1.0 reads a primary-key table in batch mode (fluss.apache.org, Flink Reads, version 1.0).
- Readiness: the tablet server has no health check and registers in ZooKeeper some seconds after it starts (`compose-store.yml:63-90`; `docs/guides/fluss.md:20`, `83-86`). `run.sh` waits for `/fluss/tabletservers/ids` to list `0` before the SQL, with a limit: odctl's test allows 24 tries at 5 seconds (`smoke.sh:1398-1403`); the guide's example has no limit (`fluss.md:84`).
- The check reads the table and compares it with the expected rows, 1 at 12.50, 2 at 19.00 and 3 at 7.00, and exactly 3 rows; it exits 1 on any difference and when the client printed an error or no rows.

## Wrong answers seen or expected

- A6: a deduplicating query, or a log table with a view over it, stated to be needed because Fluss keeps every row; a statement that a primary-key table keeps the first row.
- A10: a check that only counts rows, only looks for one price, or greps the client's output so that an error or an empty result still exits 0.
- A2: running the SQL straight after `odctl up` with no wait for the tablet server, or a wait with no limit.
- A12: a wait limit or interval with no reason.
- A3 (counted, not a kind of this case's focus): `127.0.0.1:9123` or `localhost:9123` in the catalog.
