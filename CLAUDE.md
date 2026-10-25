# odctl

A CLI that starts a local open data stack with Docker Compose profiles: Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, MLflow, Feast, Airflow, Temporal, Marquez, OpenMetadata, Grafana and more.

`CONTRIBUTING.md` holds the set-up, the code map, the test commands, the rules for code and docs, how to add a profile or a command, and the release steps. Read it before a change. This file holds only what applies to an agent.

## Running the Tests

- Run the unit suite, `pytest tests/`, in full once before each commit, never after each step.
- Run the strict build at most once per commit.

## Owner Decisions

- Show any Renovate config change to the owner before making it.
- Real projects find defects the profile e2e tests miss, so run the benchtop projects on a released odctl from time to time, when the owner asks. It is not a release step: each project starts a full compose stack, which takes too long to do at every release.

## Git

- Commit or push only when asked. Do not create branches unless asked.
- Merge a bot PR with the owner as author: `gh pr merge <n> --squash --author-email <maintainer email>`. A plain squash merge adds the bot to the contributors list. If a bot commit lands on `main`, rewrite it with the maintainer as author and rename the default branch and back so GitHub recounts contributors. Do this only with the owner's approval: the rewrite changes pushed history and needs a force push, and each force push is approved on its own.
