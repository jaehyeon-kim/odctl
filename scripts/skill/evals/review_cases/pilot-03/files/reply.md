# Changing odctl's PostgreSQL time zone to Australia/Sydney

I wrote `change_tz.sh`, which sets the time zone on the running database and keeps all your data. I haven't run it: this machine has no Docker. I've only checked that the script's syntax is valid, so it hasn't been tested against a live server.

## The `.env` change and `odctl recreate` won't work

The obvious route is to set `TZ=Australia/Sydney` in `.odctl/.env` and run `odctl recreate postgres`. That would **not** change `SHOW timezone`:

- When the database's storage was first set up, PostgreSQL saved `timezone = 'UTC'` in its own config file. Your existing data volume keeps that file, so a new container started with a different `TZ` still reports UTC.
- `recreate` also replaces the container, so the database goes down for a while.

The script uses `ALTER SYSTEM SET timezone` followed by a config reload instead. It needs no restart and doesn't touch your databases.

## What the script does

`change_tz.sh` runs these steps in order and stops at the first error:

1. Runs `py/bin/odctl ps --json` and checks that the `postgres` container is running.
2. Prints the current time zone and checks that the server knows `Australia/Sydney`.
3. Lists any time zone set for a single database or user. Such a setting overrides the server default, so the change won't apply where one exists. If one shows up, remove it with `ALTER DATABASE … RESET timezone` or `ALTER ROLE … RESET timezone`.
4. Runs `ALTER SYSTEM SET timezone = 'Australia/Sydney'`, which saves the setting in the data volume, then `SELECT pg_reload_conf()`.
5. Opens a new session and checks that `SHOW timezone` returns `Australia/Sydney`. It exits with an error if not.

Run it from this folder, where `py/bin/odctl` is, as `./change_tz.sh`. It connects as `user` / `password` using `docker exec` on the `postgres` container.

## Before you run it

- **Stored data doesn't change.** `timestamptz` values are stored in UTC, so they're the same instants as before but now display in Sydney time. Plain `timestamp` values (without a time zone) don't change at all.
- **Queries that depend on the time zone will return different results.** This includes `now()::date`, `CURRENT_DATE`, `date_trunc('day', …)`, casts between `timestamp` and `timestamptz`, and day boundaries in reports. Check any jobs or dashboards (Airflow, Metabase, etc.) that rely on UTC days.
- **Some clients set their own time zone when they connect.** JDBC clients such as Trino, Metabase, the Iceberg catalog, Marquez and OpenMetadata, and any client with `PGTZ` set, use their own time zone. They'll keep seeing their own value, and only clients that don't set one get the new default.
- **The setting is lost if the volume is deleted.** It's saved in the data volume, so it survives `odctl restart` and `odctl recreate`. `odctl down postgres --volumes` deletes the volume, and a fresh database would start in UTC again. In that case, run the script again or set `TZ=Australia/Sydney` in `.odctl/.env` *before* the database is first created.
- **Only `timezone` changes.** Server log timestamps (`log_timezone`) stay in UTC. If you want those in Sydney time too, add `ALTER SYSTEM SET log_timezone = 'Australia/Sydney'` before the reload.
- **I didn't change `.odctl/.env`.** Its `TZ` setting also applies to Flink, Spark and MLflow, so changing it would affect those services the next time they're recreated.

To undo it, run `ALTER SYSTEM RESET timezone; SELECT pg_reload_conf();`.
