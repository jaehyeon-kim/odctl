# pg-load-container

Answer sheet of the case `pg-load-container`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A9 (state from an earlier run breaks the next), A8 (image content assumed).

## Records

- github `jaehyeon-kim/odctl#20` and planning `architecting-analytics/review-labs.md:39` (HIGH 1): an address from the wrong side, and guessed host names and logins.
- planning `architecting-analytics/validation-live-stack.md:55`: a table created eight times without `IF NOT EXISTS`.
- planning `architecting-analytics/validation-live-stack.md:146`: an image assumed to hold a library it does not.

## Right answer

- The container joins the `odctl` network and reaches PostgreSQL as `postgres:5432`, with `user`/`password` and the database `odctl` (`docs/how-it-works.md:57`; `src/odctl/resources/compose-infra.yml:11`, 14-15, 19-21; the skill's postgres notes: "Internal (Docker): jdbc:postgresql://postgres:5432/odctl"). For example `docker run --rm --network odctl -v "$PWD":/work -w /work python:3.12-slim sh -c 'pip install ... && python load_orders.py'`, as `docs/how-it-works.md:252-260` runs boto3 in a container.
- `odctl up postgres` first, or a statement that it must run; it waits for the health check (`compose-infra.yml:52-57`).
- The schema `dev` exists in the `odctl` database (`src/odctl/resources/postgres/01-init-databases.sh:16-18`); `CREATE SCHEMA IF NOT EXISTS dev` is also right.
- A stock image such as `python:3.12-slim` has no PostgreSQL driver (inferred from the official Python image, which installs Python and pip only; not checked at a tag), so the run installs one with a pinned version (`psycopg[binary]==<version>` or `psycopg2-binary==<version>`), or builds an image that holds it.
- Safe to run every night: `CREATE TABLE IF NOT EXISTS dev.orders`, and the night's full export replaces the rows, by `TRUNCATE` and load in one transaction, or by an upsert on `order_id` that also removes orders no longer in the export. Inserting the file again each night duplicates every order.

## Wrong answers seen or expected

- A3: `localhost`, `127.0.0.1` or `host.docker.internal` as the host in the container. `--network host` is not counted: it works on Docker Engine on Linux and on Docker Desktop 4.34 and later once enabled (Docker docs, Host network driver), though the container then reaches PostgreSQL at the host port, not `postgres:5432`.
- A3: a host name such as `odctl-postgres` or `db`, or a login other than `user`/`password`.
- A9: a plain `CREATE TABLE` with no `IF NOT EXISTS`, or an `INSERT` of every row each night with no truncate or upsert.
- A8: `import psycopg` in a stock Python image with no install step, or a stated claim that the image holds the driver.
- A8: the file read from a path the container cannot see, with no `-v` mount of the folder.
