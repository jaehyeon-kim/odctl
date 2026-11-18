# pg-port-clash

Answer sheet of the case `pg-port-clash`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (stack setting or workspace file assumed), A3 (address from the wrong side), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.8.0/review-round1.md:20` (M7): a setting said to change through an upstream setting, when in odctl only an edit of the workspace's compose file and a recreate change it.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): the container address `catalog:8181` put where the host reads it; here the host port and the container port are the two sides.

## Right answer

- The host port is the left side of `"127.0.0.1:5432:5432"` in the workspace's `.odctl/compose-infra.yml` (`src/odctl/resources/compose-infra.yml:13`). The change is that line to `"127.0.0.1:5433:5432"`, in the workspace copy, as `docs/how-it-works.md:182-190` does for Trino's port. `odctl init` has already made the workspace (the prompt says so), and odctl reads the workspace's files when it exists (`docs/how-it-works.md:122`).
- Then `odctl up postgres`. A container left by the failed start is replaced, because its configuration changed (Docker docs, `docker compose up`: "If there are existing containers for a service, and the service's configuration or image was changed after the container's creation, `docker compose up` picks up the changes by stopping and recreating the containers"); `odctl recreate postgres` before `up`, or after it, is not wrong. `odctl up postgres` waits for the health check (`docs/how-it-works.md:34`; `compose-infra.yml:52-57`), so no extra wait is needed.
- The application on the host uses `postgresql://user:password@127.0.0.1:5433/odctl` (database `odctl`, login `user`/`password`, `compose-infra.yml:19-21`; the skill's postgres notes).
- The container port stays 5432, so every container on the `odctl` network still uses `postgres:5432`: the catalog (`compose-infra.yml:171`), MLflow (`compose-mlops.yml:107`) and the others need no change.
- No `.env` key sets the port: `odctl init` writes only the keys in `src/odctl/workspace.py:101-165`, and the compose file has no variable in that line.
- `odctl init --force` later copies the bundled file again and removes the edit (`docs/how-it-works.md:267`); saying so is right but not required.

## Wrong answers seen or expected

- A8: an edit of the compose file inside the installed package, or a copy of it outside `.odctl/`.
- A8: a `POSTGRES_PORT`, `PGPORT` or `PORT` line in `.odctl/.env` with no edit of the compose line that would read it; no such key sets the port. A run that changes the workspace's port line to `"127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432"` and sets that key in `.odctl/.env` is right, because Compose reads `.odctl/.env` (`src/odctl/docker.py:281-299`).
- A4: an option of `odctl up` that sets a port; `up` takes only `--dry-run` and `--pull` (`src/odctl/main.py:405-419`).
- A3: `"127.0.0.1:5433:5433"`, or `-c port=5433`, which moves the container port and breaks `postgres:5432` for the catalog and the other profiles.
- A3: telling the user to point other odctl profiles or containers at port 5433.
- A3: a host URL with `postgres` as the host name, or with port 5432.
- A4: a `pg_isready` loop after `odctl up postgres`, which already waits for the health check.
