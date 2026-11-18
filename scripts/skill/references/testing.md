# odctl in Tests and CI

A project's tests or CI job start the profiles they need, run their setup and checks, and stop what they started. This page covers each of those steps.

## Pin the Version

Install a fixed odctl version, such as `uv tool install odctl==<version>`. Without a workspace, odctl tags its own images with the CLI version. A committed `.odctl/` workspace keeps the `TAG` in its `.env` that `odctl init` wrote, so after changing the pinned version, keep a copy of the workspace's edits, run `odctl init --force --yes`, and make the edits again. A `TAG` set in the shell overrides both, so a CI job leaves it unset.

## Start

- `odctl up <profiles>` asks no question and returns once every service is running, and healthy where it has a health check. Run `odctl up <profiles> --dry-run` first when writing the job, to see every profile it starts.
- `odctl init --force` asks for confirmation before it replaces the workspace, so a script passes `--yes`.
- A test waits on the check it needs, with a limit, as [SKILL.md](../SKILL.md), How to Use It, sets out.

## Stop

- Tear down only the profiles the tests started, with `odctl down <profiles>`, which asks no question. It does not stop their dependencies, such as `postgres` under `trino`, so name those too when the job should stop them.
- Add `--volumes` only on a CI runner, where the data is the tests' own. On a developer's machine the volumes can hold the developer's own data. `odctl down <profiles> --volumes` asks for confirmation when the named profiles and their dependencies cover every profile that has containers, as on a CI runner that ran only the tests, so a CI script passes `--yes`.
- `odctl down --all --volumes --yes` stops and removes everything odctl runs. Use it only on a CI runner that started with no containers.

## Run the Setup Twice

A second run on the same stack starts from what the first run left, such as a table, a topic, a registered job or a stored row. Each setup step is safe to run on that state:

- Create with `IF NOT EXISTS`, or the service's own form of it.
- Delete what the step registers before it registers it again, such as a connector, a streaming job or a DAG run.
- Check only what this run wrote, such as rows with this run's id, not a count that rows from an earlier run already pass.

Run the whole setup twice on one stack before relying on it.
