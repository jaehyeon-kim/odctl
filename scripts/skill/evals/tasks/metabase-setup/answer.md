# metabase-setup

Answer sheet of the case `metabase-setup`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository. Paths that start with `src/metabase/` are in Metabase at tag `v0.64.3.5`, the image's version (`src/odctl/resources/compose-analytics.yml:199`).

The script calls Metabase from the host, and the database address it gives Metabase is used from the `metabase` container, so the case covers the `metabase` profile from both sides.

Kinds: A3 (address from the wrong side, or guessed), A9 (state from an earlier run breaks the next), A7 (what a command keeps or removes).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.
- planning `architecting-analytics/validation-live-stack.md:55`: a create step that was not safe to run twice.
- planning `odctl/release/1.6.0/review-round1.md:7` (S1): what a teardown removes was left out or guessed.

## Right answer

- From the laptop Metabase is `http://127.0.0.1:3000` (`src/odctl/resources/registry.yml:201-204`; `compose-analytics.yml:206`). `odctl up metabase` waits for its health check on `/api/health` (`compose-analytics.yml:219-220`; `docs/how-it-works.md:34`), so the script needs no extra wait after it; a bounded wait on `/api/health` is not counted.
- First setup: the setup token is a public setting returned by `GET /api/session/properties` as `setup-token` (`src/metabase/setup/settings.clj:9-14`; `src/metabase/session/api.clj:461`), and `POST /api/setup` takes `token`, `user` (`email`, `password`) and `prefs` (`site_name`) and creates the first admin (`src/metabase/setup_rest/api.clj:64-80`). Then `POST /api/session` with `username` and `password` gives the session id sent as `X-Metabase-Session` (`src/metabase/session/api.clj:239-245`; `.github/scripts/smoke.sh:645-658`).
- The database is added with `POST /api/database`, engine `postgres` and details `host` `postgres`, `port` 5432, `dbname` `odctl`, `user` `user`, `password` `password` (`src/metabase/driver/common.clj` field names `host`, `port`, `dbname`, `user`, `password`; `docs/guides/trino-metabase.md:52-58`; `smoke.sh:696-698`). Metabase connects from its container on the `odctl` network, so `127.0.0.1` or `localhost` there is the Metabase container itself (`docs/guides/trino-metabase.md:58`). `POST /api/database` tests the connection first and answers 400 without creating the database when it fails (Metabase `v0.64.3.5`, `src/metabase/warehouses_rest/api.clj:780-813`), so a 200 there shows Metabase reached the host; a query through the database is also right as the check.
- Safe to run again: `POST /api/setup` refuses once a user exists (`setup_rest/api.clj:37-46`), and the setup token is cleared then (`setup_rest/api.clj:91-94`), so the script runs the setup only while `setup-token` is set and otherwise logs in. `POST /api/database` checks no name and inserts a new row every time (`src/metabase/warehouses_rest/api.clj:754-800`; `warehouses_rest/db.clj:233-236`), so the script first lists `GET /api/database` and adds `odctl warehouse` only when no database has that name (`smoke.sh:663-679`).
- Metabase keeps its users, questions and dashboards in the `metabase` database on odctl's PostgreSQL (`compose-analytics.yml:211-216`; `docs/guides/trino-metabase.md:3`). `stop.sh` is `odctl down metabase`, which acts only on that profile and leaves `postgres` running (`docs/how-it-works.md:49`), and `start.sh` is `odctl up metabase`; the dashboards stay. `odctl restart` does not free the memory, because it keeps the container running.

## Wrong answers seen or expected

- A3: `"host": "localhost"` or `"127.0.0.1"` for the database; `http://metabase:3000` from the laptop.
- A9: `POST /api/setup` on every run with no check, so the second run fails; `POST /api/database` on every run, so a second `odctl warehouse` appears.
- A7: `odctl down metabase postgres`, `odctl down --all`, or `--volumes` in `stop.sh`; a statement that `odctl down metabase` loses the dashboards, or a backup step said to be needed for that reason.
