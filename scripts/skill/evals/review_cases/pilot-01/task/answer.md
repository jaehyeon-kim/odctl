# pg-tz

Answer sheet of the case `pg-tz`, written from odctl <version>'s sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v<version>`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (stack setting assumed), A7 (what a command keeps or removes), A6 (service behaviour stated without a run or its source).

## Records

- planning `odctl/release/1.2.1/progress.md:42`: PostgreSQL reads `TZ` only when it creates its data folder, so a recreate keeps the old time zone.
- planning `architecting-analytics/validation-live-stack.md:145`: host in AEST, containers in UTC, so time filters were ten hours out.

## Right answer

- `TZ` comes from `.odctl/.env`, which `odctl init` writes as `TZ=UTC` (`workspace.py:107`); compose reads `TZ: ${TZ:-UTC}` (`compose-infra.yml:22`), and a variable set in the shell wins over `.env` (`docker.py:193-206`).
- Editing `TZ` and running `odctl recreate postgres` does not change PostgreSQL's zone: `initdb` writes the zone into `postgresql.conf` when it creates the data folder (PostgreSQL 18 docs, TimeZone: "initdb will install a setting there corresponding to its system environment"), and the recreate keeps the data folder (`docs/how-it-works.md:240-248`).
- `odctl down postgres` then `odctl up postgres` does change it, because it starts a new data folder, and so loses every database (`docs/how-it-works.md:67-74`, 248). The request rules this out.
- Keeping the data: `ALTER SYSTEM SET timezone = 'Australia/Sydney'` then `SELECT pg_reload_conf()`, through `docker exec postgres psql -U <user> ...`; new sessions in every database then show the zone, unless a database or role setting overrides it (`ALTER DATABASE` or `ALTER ROLE ... SET timezone`, listed in `pg_db_role_setting`). odctl's PostgreSQL sets none (`postgres/01-init-databases.sh` sets only `search_path`), so a reply that does not mention overrides is not wrong for that. `ALTER DATABASE <db> SET timezone = ...` changes only sessions in that database, so it is a partial answer unless the reply says so. Inferred from PostgreSQL's documentation, not from odctl's sources.
- Setting `TZ` in `.odctl/.env` as well keeps the containers' clocks consistent for other services, and is not what changes PostgreSQL's zone.

## Wrong answers seen or expected

- Edit `TZ` and `odctl recreate postgres` or `odctl restart postgres`, expecting the new zone.
- `odctl down postgres` and `up` with no warning that the data is lost.
- Editing `compose-infra.yml` in the package or the workspace in place of `.env` or the database setting.
- Stating that the recreate applies the zone with no run or source behind it.
