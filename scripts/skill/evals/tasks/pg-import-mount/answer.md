# pg-import-mount

Answer sheet of the case `pg-import-mount`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (workspace file assumed), A7 (what a command keeps or removes), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.8.0/review-round1.md:20` (M7): a setting said to change one way, when in odctl only an edit of the workspace's compose file and a recreate change it.
- planning `odctl/release/1.2.1/progress.md:41`: a recreate keeps PostgreSQL's data through its volume.
- planning `odctl/release/1.6.0/review-round2.md:9` (S1): a command marked as keeping data when it replaced the container.

## Right answer

- An override file is not read. odctl runs each compose file by passing it as the only file (`src/odctl/docker.py:47-49`, `compose_files=[...]`, which python-on-whales passes as `--file`). Compose reads `compose.override.yaml` only when it looks for the files itself (Docker docs, "Merge Compose files": "By default, Compose reads two files, a `compose.yaml` and an optional `compose.override.yaml` file"; `docker compose` reference: the lookup happens "If you don't provide this flag"). So a `compose.override.yml` in `.odctl/` or in the project changes nothing. Inferred from those docs and the source, not from a run.
- The mount goes into the workspace's `.odctl/compose-infra.yml`, under the `postgres` service's `volumes:` (`src/odctl/resources/compose-infra.yml:49-50`), as a new line such as `- ../exports:/import:ro`. A relative path is resolved from the folder of the compose file, `.odctl/`, as `./postgres/01-init-databases.sh` on line 50 is (Docker docs, `docker compose` reference: `--project-directory` defaults to "the path of the, first specified, Compose file"). So `./exports` there names `.odctl/exports`, which is wrong; `../exports` or an absolute path is right.
- `odctl recreate postgres` applies it (`docs/how-it-works.md:159`) and keeps the databases, because PostgreSQL's data volume passes to the new container (`docs/how-it-works.md:67`, 72; the recreate prints so, `src/odctl/main.py:1148`). It waits for the health check (`src/odctl/projects.py:81-86`). It acts on `postgres` only (`docs/how-it-works.md:49`); profiles that use PostgreSQL lose their connections while it restarts.
- A check such as `docker exec postgres ls /import` shows the files are there.

## Wrong answers seen or expected

- A8: a `compose.override.yml` (or `docker-compose.override.yml`) as the change, or `COMPOSE_FILE` set to add one, stated to work with odctl.
- A8: `./exports:/import` in `.odctl/compose-infra.yml`, which mounts `.odctl/exports`.
- A8: an edit of the compose file inside the installed package.
- A7: `odctl down postgres` and `odctl up postgres`, which loses every database (`docs/how-it-works.md:73`), or a statement that `recreate` loses the data.
- A4: `odctl restart postgres` to apply the edit; a restart keeps the container and does not apply a compose change (`docs/how-it-works.md:159`).
- A8: `docker compose -f .odctl/compose-infra.yml -f compose.override.yml up -d postgres` run by hand, with no statement that the next `odctl up` or `odctl recreate` of `postgres` runs the file alone and so drops the mount (inferred from `docker.py:47-49` and the Compose `up` docs, which recreate a container whose configuration changed).
