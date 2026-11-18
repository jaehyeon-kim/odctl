# ch-insert-read

Answer sheet of the case `ch-insert-read`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (stack setting assumed), A6 (service behaviour stated without a run or its source), A9 (state from an earlier run).

## Records

- planning `architecting-analytics/validation-live-stack.md:143`: the stack's async insert setting made insert-then-read racy. In odctl 1.9.0 that setting is `wait_for_async_insert=1` (`clickhouse/users.xml:22-23`, since `e7f7549`), so the insert waits until the row is written.

## Right answer

- `odctl up ch-lite`; `ch-11` and `ch-12` have health checks (`compose-analytics.yml:15`), so `up` waits for them.
- From the host: HTTP `127.0.0.1:8123`, native `127.0.0.1:9000` (`ch-11`); login `default` / `password`.
- Insert, then select straight away: `async_insert=1` with `wait_for_async_insert=1` for the default profile (`clickhouse/users.xml:15-23`) makes the insert return after the row is written. `docs/snippets/clickhouse/commands.sh` `merge-tree` (lines 9 to 18) and `smoke.sh` `smoke_ch_lite` (461 to 470) do this.
- The table has a name unique to the run, or the create fails when the table exists, and it is dropped after, also when the test fails (a fixture's teardown or `try`/`finally`), so a second run on the same stack passes and no table the run did not create is dropped. A fixed name with `IF NOT EXISTS` and a drop after would drop a table that was there before.

## Wrong answers seen or expected

- A `sleep`, `SYSTEM FLUSH ASYNC INSERT QUEUE` or a retry loop, with a claim that the read is racy, without reading `users.xml`.
- Setting `wait_for_async_insert=0`.
- No password.
- A fixed name with a plain `CREATE TABLE` and no drop, which fails on the second run.
