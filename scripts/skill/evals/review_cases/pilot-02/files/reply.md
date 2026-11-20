I wrote `change_tz.sh`. I did not run it, because Docker isn't available here. Nothing is tested.

**What `change_tz.sh` does**
1. Checks that the `postgres` container is up.
2. Prints the current `timezone` and any per-database or per-role `timezone` overrides.
3. Runs `ALTER SYSTEM SET timezone = 'Australia/Sydney'` and `pg_reload_conf()`.
4. Runs `SHOW timezone` on a new connection. It should print `Australia/Sydney`.

**What to know before you run it**
- **I did not change `TZ` in `.odctl/.env` and then run `odctl recreate postgres`, on purpose.** odctl keeps Postgres data inside the container, so `recreate` would delete your databases. `TZ` also affects Flink, Spark and MLflow. The initdb-written `postgresql.conf` would also keep `UTC` on an existing data directory. The script changes the setting live, with no restart, and your data stays in place.
- **The change is stored in the container's data directory.** It survives `odctl restart postgres`. It is lost on `down` or `recreate`, which wipe the data anyway. If you rebuild later, add `-c timezone=Australia/Sydney` to the postgres `command:` in `.odctl/compose-infra.yml`. I left that file alone because you asked for only two files.
- **Connections that are already open keep `UTC`.** Apps need to reconnect, and long-lived pools such as Airflow, Metabase and Trino may need a restart.
- **Timestamps with a time zone** keep the same instant but display in Sydney time. **Timestamps without a time zone** are stored values and don't change. Code that relies on `now()` or `::timestamp` casts will behave differently.
- **Overrides:** if step 2 lists a `timezone` override on a database or role, that override still wins over the server setting. You would need to clear it with `ALTER DATABASE ... RESET timezone`.
- **Log timestamps:** `log_timezone` is separate, and I left it as it is.
- **Container name and login:** the script assumes the container is named `postgres` and the login is `user` on database `odctl`, the defaults.
