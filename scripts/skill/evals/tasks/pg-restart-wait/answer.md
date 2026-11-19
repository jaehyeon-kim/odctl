# pg-restart-wait

Answer sheet of the case `pg-restart-wait`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A2 (service called before it is ready), A12 (a number with no reason), A10 (a check that cannot fail), A4 (odctl CLI behaviour assumed), A7 (what a command keeps or removes).

## Records

- planning `odctl/release/1.8.0/reader-check.md:16` (fix 4): a service answered Service Unavailable after `odctl restart telemetry`.
- planning `odctl/release/1.4.0/review-batch1-round3.md:21` (check 3): a fixed wait of a few seconds with no measurement, replaced by a repeat until success.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit.
- planning `odctl/release/1.4.0/review-batch1-round3.md:6` (S2): a failed step hidden because the script did not stop on it.
- A12 has no odctl record; this case extends the kind's evidence from desflow (planning `odctl/plan-agent-skill.md`, Kinds, A12).

## Right answer

- `odctl restart postgres` runs `docker compose restart` (`src/odctl/projects.py:41-49`), which has no option to wait for health (Docker docs, `docker compose restart`: its options are `--no-deps` and `--timeout`), unlike `up` and `recreate`, which pass `wait=True` (`src/odctl/docker.py:482`; `projects.py:81-86`). So `restart` returns before PostgreSQL accepts connections again, and the migrations need a wait. The review rubric says the same (`scripts/skill/evals/review_rubric.md`, A2: "`restart` runs `docker compose restart`, which does not wait for health").
- The wait repeats a check of what the migrations need, with a limit, such as `docker exec postgres pg_isready -U user -d odctl` (the health check runs `pg_isready` too, with `-d metabase`, `src/odctl/resources/compose-infra.yml:53`) or a `psql -c 'SELECT 1'`, and stops the script with an error when the limit is reached. Its count and delay carry their reason, for example the health check's own limit: a check every 5 seconds, 10 retries, after a 10 second start period (`compose-infra.yml:54-57`).
- `odctl recreate postgres` in place of `restart` is also right: it waits for the health check and keeps the data (`docs/how-it-works.md:72`). A reply that uses it needs no extra wait.
- The job fails when a migration fails: `set -euo pipefail` (or a check of each `psql` exit status), and `psql -v ON_ERROR_STOP=1`. The old script reported success because a `for` loop's status is that of its last command, so a failed first file is hidden when the last succeeds; and psql exits 0 after an SQL error in a script unless `ON_ERROR_STOP` is set (PostgreSQL docs, psql, Exit Status: 2 "if the connection to the server went bad and the session was not interactive", 3 "if an error occurred in a script and the variable ON_ERROR_STOP was set").
- `restart` keeps the container and its data (`docs/how-it-works.md:71`).

## Wrong answers seen or expected

- A2: no wait after `odctl restart postgres`, a fixed `sleep`, or a loop with no limit.
- A12: a retry count, delay or timeout with no reason.
- A4: a statement that `odctl restart` waits for the health check.
- A10: no `ON_ERROR_STOP=1`, no `set -e`, or `|| true` on the migration loop, so a failed migration still ends with exit 0.
- A10: a wait loop that ends after its limit and carries on to the migrations, exiting 0.
- A7: `odctl down postgres` and `odctl up postgres` to drop the connections, which loses every database (`docs/how-it-works.md:73`).
