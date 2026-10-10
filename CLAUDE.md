# odctl

A CLI that starts a local open data stack with Docker Compose profiles: Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, MLflow, Feast, Airflow, Temporal, Marquez, OpenMetadata, Grafana and more.

## Layout

| Path | Contents |
|---|---|
| `src/odctl/main.py` | the Typer CLI (`list`, `explain`, `ps`, `info`, `init`, `pull`, `up`, `down`, `logs`, `restart`, `recreate`) |
| `src/odctl/registry.py`, `resources/registry.yml` | profiles, the services in each, dependencies, ports and usage text |
| `src/odctl/planner.py`, `docker.py`, `workspace.py`, `config.py`, `ui.py` | startup order, Docker Compose calls, the `.odctl` workspace, settings, terminal output |
| `src/odctl/resources/compose-*.yml` | one compose file per area (kafka, flink, spark, store, analytics, mlops, orch, obsv, metadata, infra, deps) |
| `src/odctl/resources/docker/` | odctl's own images (postgres, mlflow, airflow, spark), published to `ghcr.io/jaehyeon-kim/odctl/<name>:<version>` |
| `src/odctl/resources/deps/` | the `deps` image: connector and engine jars built or downloaded into the `odctl-shared-deps` volume; versions in `versions.env` |
| `scripts/gen_pages.py` | builds a page per technology and the CLI reference at docs build time, from `registry.yml`, the compose files and `--help` |
| `.github/scripts/smoke.sh` | the e2e assertions per profile group; `select-profiles.py` chooses the groups |
| `docs/` | MkDocs Material site, versioned with mike |

## Commands

```bash
uv run pytest tests/ -q
uvx pre-commit run --all-files                    # ruff, ruff format, mypy, whitespace, YAML, TOML
DISABLE_MKDOCS_2_WARNING=true uv run mkdocs build --strict
uv run mkdocs serve -a 127.0.0.1:8000             # docs at http://127.0.0.1:8000/odctl/
```

## Rules

- **Images follow the CLI version.** odctl runs its own images at its own version (`TAG`), never `latest`: Docker does not pull a tag it already has, so a cached `latest` keeps running old code. Third-party images are pinned to a version and updated by Renovate.
- **Bind to 127.0.0.1.** Every published port binds to `127.0.0.1`, not all interfaces.
- **One profile per tool**, with `-lite` and `-full` variants where a tool has a small and a clustered form (`kafka-lite`, `kafka-full`).
- **Fixed container names.** Every service has a `container_name`, so `odctl up` cannot scale a service; several copies are separate named services (Flink's `taskmanager-a` and `taskmanager-b`).
- **Docs pages that list versions or ports are generated** by `scripts/gen_pages.py`; do not copy those values into hand-written guides. Guide commands come from the e2e tests.
- **e2e runs only on tags and manual dispatch**, because a PR's images for an unreleased version do not exist yet. A PR gets lint, unit tests, image builds when image inputs change, and the strict docs build.
- **Renovate PRs** open on Mondays, image updates grouped by compose file. Show any Renovate config change to the owner before making it.
- **Writing.** Plain English for non-native readers. No em or en dashes. Headings do not start with "The". Markdown paragraphs are one line each, never hard-wrapped.

## Release

1. Bump `version` in `pyproject.toml` and run `uv lock`; push to `main`. The docs deploy as that version, aliased `latest`.
2. Push tag `vX.Y.Z`. The tag pipeline builds and pushes the `X.Y.Z` images, then runs e2e for every profile group (about an hour).
3. Publish the GitHub release. `publish.yml` waits for a green tag pipeline and checks that every `X.Y.Z` image is in ghcr, then uploads to PyPI.

## Git

- Commit or push only when asked. Do not create branches unless asked.
- Merge a bot PR with the owner as author: `gh pr merge <n> --squash --author-email <maintainer email>`. A plain squash merge adds the bot to the contributors list. If a bot commit lands on `main`, rewrite it with the maintainer as author and rename the default branch and back so GitHub recounts contributors.
