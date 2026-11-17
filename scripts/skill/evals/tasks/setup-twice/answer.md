# setup-twice

Answer sheet of the case `setup-twice`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A9 (state from an earlier run breaks the next), A2 (service called before it is ready), A10 (a check that cannot fail).

## Records

- planning `odctl/release/1.4.0/review-batch1-round3.md:5`: `airflow dags unpause` exits 0 before the DAG is parsed, and the DAG stays paused.
- planning `odctl/release/1.4.0/review-batch1-round3.md:6` and `:7`: `feast teardown` left rows that broke the next apply; the create step was not safe to run twice; a failed apply was hidden without `pipefail`.
- planning `odctl/release/1.4.0/review-batch1-round2.md:12`: the DAG was left unpaused in the bucket, so the second run failed.
- planning `architecting-analytics/validation-live-stack.md:55`: a table created eight times without `IF NOT EXISTS`.

## Right answer

- Each step is safe to run twice on one stack: the table is created with `create_table_if_not_exists` or dropped first (`docs/guides/feast-iceberg.md:41`; `smoke.sh:952` deletes it with `DELETE /v1/namespaces/demo/tables/driver_stats?purgeRequested=true`, accepting 204 or 404); rows are not appended twice.
- The Feast cleanup is `feast -c feature_repo delete driver_stats`, never `feast teardown` (`smoke.sh:957`, 1853, comments 1792 to 1794).
- After the upload, wait with a limit until Airflow lists the DAG before `dags unpause` and the trigger (`smoke.sh:964-965`, 881; `feast-iceberg.md:202`).
- A failure stops the script: `set -euo pipefail`, and no `|| true` on a step that must succeed.
- At the end, or at the start of the next run, the DAG is paused and its file removed from `s3://airflow`, or the script handles a DAG already there (`smoke.sh:993-999`).

## Wrong answers seen or expected

- `dags unpause` straight after the upload.
- `feast teardown` for the cleanup.
- A plain `CREATE TABLE`, or an append of the same rows on every run.
- `|| true` on the apply or the create.
- A fixed `sleep` for the DAG parse.
