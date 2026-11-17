# Reply: PostgreSQL time zone change

## What I wrote

- **`change_tz.sh`**: a bash script that sets PostgreSQL's time zone to `Australia/Sydney` and checks it with `SHOW timezone`.
- **`reply.md`**: this file.

I did not run the script. Docker is not available on this machine, so I could not test it here. I checked only the syntax with `bash -n`.

## What the script does, in order

1. `py/bin/odctl up postgres` starts the postgres profile and its dependency, `deps`, if they are not running.
2. Waits up to about 60 seconds for `pg_isready` to succeed inside the `postgres` container.
3. `ALTER SYSTEM SET timezone = 'Australia/Sydney'`, run as `user` in the `odctl` database. This writes `postgresql.auto.conf` in the data volume.
4. `SELECT pg_reload_conf()` applies the change without a restart.
5. Runs `SHOW timezone` and exits with an error unless the result is exactly `Australia/Sydney`.

## Things you must know before running it

- **I did not change `.odctl/.env`.** It still sets `TZ=UTC`, and every service that reads `${TZ}` uses it. Changing it would move those services too, and you asked only for PostgreSQL. The fix is therefore set inside PostgreSQL itself.
- **Why not just edit `TZ`:** the postgres data volume already has `timezone = 'Etc/UTC'` (or similar) in `postgresql.conf`, written by initdb on first start. Changing `TZ` and recreating the container would not change `SHOW timezone`. `ALTER SYSTEM` overrides that value and survives restarts and `odctl recreate`.
- **Data is kept.** The script does not run `odctl down` or `--volumes`, so no volume is removed. Do not run `odctl down --volumes` later, or the setting is lost along with the data.
- **Run it from anywhere:** it changes into its own folder, so the `py/bin/odctl` path resolves. It needs Docker running and the `postgres` container name unchanged.
- **Per-database overrides:** if any database has its own `timezone` setting (`ALTER DATABASE ... SET timezone`), it still wins for that database. The script checks only the `odctl` database. To see overrides, run: `docker exec postgres psql -U user -d odctl -c "SELECT datname, setconfig FROM pg_db_role_setting;"`
- **Existing sessions** pick up the new value on reconnect; sessions that set their own time zone keep theirs.
- **Other services** keep their current time zone (`UTC`). If you also want them in Sydney, change `TZ` in `.odctl/.env` and run `odctl recreate <profile>` for each profile. That is a separate decision.

## How to run

```bash
cd <your odctl workspace folder>
./change_tz.sh
```

Expected last line: `SHOW timezone -> Australia/Sydney`.
