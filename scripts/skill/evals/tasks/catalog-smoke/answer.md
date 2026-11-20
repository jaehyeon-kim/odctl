# catalog-smoke

Answer sheet of the case `catalog-smoke`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A10 (a check that cannot fail), A2 (service called before it is ready), A12 (a number with no reason), A9 (state from an earlier run breaks the next), A3 (address from the wrong side).

## Records

- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1): a `grep` that also matched another key, so the check could not fail.
- planning `odctl/release/1.4.0/audit.md:11` (M1): `|| true` hid a failure.
- planning `odctl/release/1.4.0/audit.md:10` (S2): a second smoke run on one stack failed or passed on the first run's values.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit. A12 has no odctl record; this case extends the kind's evidence from desflow (planning `odctl/plan-agent-skill.md`, Kinds, A12).

## Right answer

- `odctl up catalog` returns when `iceberg-catalog` runs, not when it answers: the `catalog` service has no health check (`src/odctl/resources/compose-infra.yml:122-176`; `docs/how-it-works.md:34`). So the check first waits, with a limit, for `curl -fsS http://127.0.0.1:8181/v1/config`, as odctl's smoke test does (`.github/scripts/smoke.sh:32`, 303: `retry 30 5`). Each count and delay carries its reason.
- From the host the address is `http://127.0.0.1:8181` (`compose-infra.yml:139`; the skill's catalog notes).
- An answer to `/v1/config` or a namespace is not enough for "could create a table": odctl's smoke test says "A namespace is metadata only. Creating a table exercises the JDBC catalog backend and the S3FileIO write that every engine depends on" (`smoke.sh:597-598`). The check creates a table (`POST /v1/namespaces/<ns>/tables`) and reads it back, expecting `metadata-location` (`smoke.sh:600-606`).
- Every request that must succeed fails the script when it does not: `curl -f` (or a check of the status code), `set -euo pipefail`, and no `|| true` on those steps. Plain `curl -s` exits 0 on an HTTP error status (curl manual, `--fail`: without it an error page is returned and curl exits 0; with it, curl exits 22). A `|| true` on a cleanup step, as `smoke.sh:600` has, is not a mistake.
- Safe to run twice on one stack: the check removes the table it creates, and handles one an earlier failed run left (`smoke.sh:599-600` deletes it first, "or the create gets 409"), and a namespace create that already exists is accepted or skipped. A unique name per run, removed at the end, is also right.

## Wrong answers seen or expected

- A10: `curl -s` with no `-f` and no status check, or `|| true`, or a pipe without `pipefail`, on a step that must succeed.
- A10: only `/v1/config` or a namespace listing as the whole check, stated to prove a table can be created.
- A10: `grep -q <name>` on a listing where the name can match something else, such as another namespace that contains it.
- A9: a namespace or table created with no handling of an earlier run's copy, so the second run fails with 409.
- A2: no wait after `odctl up catalog`, a fixed `sleep`, or a loop with no limit.
- A12: a retry count, delay or timeout with no reason.
- A3: `http://catalog:8181` or `iceberg-catalog:8181` used from the host.
