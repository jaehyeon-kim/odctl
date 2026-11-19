# host-pgvector-test

Answer sheet of the case `host-pgvector-test`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A11 (host environment assumed), A10 (a check that cannot fail), A9 (state from an earlier run breaks the next), A3 (address from the wrong side), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.8.0/audit.md:13` (M5): `uv venv` with no `--python` took the host's newest Python.
- planning `odctl/release/1.7.0/audit.md:9` (M3): commands needed `uv` and the page did not say so.
- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1): a check that could not fail.
- planning `architecting-analytics/validation-live-stack.md:55`: a table created again on every run without `IF NOT EXISTS`.

## Right answer

- `odctl up postgres`; it waits for PostgreSQL's health check (`docs/how-it-works.md:34`; `src/odctl/resources/compose-infra.yml:52-57`), so no extra wait is needed.
- From the host: `127.0.0.1:5432`, login `user`/`password` (`compose-infra.yml:13`, 19-21; the skill's postgres notes). The `vector` extension is already created in the database `vector` (`src/odctl/resources/postgres/01-init-databases.sh:46-51`); a test in another database runs `CREATE EXTENSION IF NOT EXISTS vector` first, which is also right.
- The test creates its own rows and asserts the id of the nearest one, as `docs/guides/hybrid-search.md:22-32` does: rows `[1,0,0]`, `[0,1,0]`, `[0.9,0.1,0]`, and `ORDER BY embedding <-> '[1,0,0]' LIMIT 1` returns the first row, because `<->` is the Euclidean distance. A test that would pass with the wrong nearest row, or with no row, cannot fail.
- Safe to run many times on one stack: the table is dropped and created again, as `docs/snippets/hybrid-search/example.sh` does (`DROP TABLE IF EXISTS`, `docs/guides/hybrid-search.md:74`), or is a temporary table, or the test's rows are removed afterwards. Ids taken from a `bigserial` after earlier runs must not be assumed to start at 1 unless the table is new.
- The environment is created with a named Python version, such as `uv venv --python 3.12 .venv` or `python3.12 -m venv`, never the bare `python3` the user describes, and the packages are pinned (for example `psycopg[binary]==<version>` and `pytest==<version>`). The script checks for, or the reply names, each host tool it needs, such as `uv`.

## Wrong answers seen or expected

- A11: `python3 -m venv .venv` or `uv venv .venv` with no Python version.
- A11: `uv` or `psql` used on the host with no check and no line in the reply.
- A10: an assertion that holds for any result, such as `assert rows is not None`, `len(rows) >= 0`, or only that the query ran.
- A10: `|| true` after the test, or `pytest ... | tee` without `pipefail`.
- A9: `CREATE TABLE` with no `IF NOT EXISTS` and no drop first, or rows inserted again on every run so that the nearest id changes.
- A3: `postgres:5432` or `host.docker.internal` from the host.
- A4: a `pg_isready` loop after `odctl up postgres`, which already waits for the health check.
