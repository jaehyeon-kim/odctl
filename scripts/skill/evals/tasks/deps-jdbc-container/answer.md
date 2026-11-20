# deps-jdbc-container

Answer sheet of the case `deps-jdbc-container`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (image content or stack setting assumed), A1 (a step needs an earlier step), A3 (address from the wrong side), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.2.0/review-batch1.md:12` (R1 2) and `architecting-analytics/validation-live-stack.md:146`: a jar assumed to be in an image, or at a place, where it is not.
- planning `architecting-analytics/review-labs.md:39` (HIGH 1): guessed host names and logins.
- A1 has no record for the shared volume; this case extends the kind's evidence from the book lab review (planning `odctl/plan-agent-skill.md`, Kinds, A1: `odctl up trino` does not start what it needs).

## Right answer

- `odctl up postgres` first. It starts `deps` before `postgres` (`odctl up postgres --dry-run`; `src/odctl/resources/registry.yml:21-22`), and `deps` creates the `odctl` network and fills the shared volume (`docs/how-it-works.md:17`). Before that the volume and the network do not exist, so the container cannot use them. `up` waits for PostgreSQL's health check (`src/odctl/resources/compose-infra.yml:52-57`), so no extra wait is needed.
- The driver is `shared/postgresql.jar` in the volume `odctl-shared-deps` (`src/odctl/resources/deps/fetch_standalone_plugins.sh:58`; volume name `src/odctl/resources/compose-deps.yml:52-54`). The catalog uses it at that path with the volume mounted on `/mnt/shared-deps` (`compose-infra.yml:135`, 144). The catalog mounts it read-only (`:ro`), as a reader should, because `init-deps` copies changed files into it on each `odctl up` (`compose-deps.yml:17-20`); Kafka Connect mounts it read-write (`compose-kafka.yml:143`).
- The run: `docker run --rm --network odctl -v odctl-shared-deps:/mnt/shared-deps:ro -v "$PWD":/app -w /app -e JDBC_URL=jdbc:postgresql://postgres:5432/odctl -e DB_USER=user -e DB_PASSWORD=password eclipse-temurin:21-jdk java -cp /mnt/shared-deps/shared/postgresql.jar DbCheck.java`. Java 11 and later run a single source file directly, with `-cp` for its libraries (JEP 330); `javac` then `java` is also right. Address and login from the skill's postgres notes ("Internal (Docker): jdbc:postgresql://postgres:5432/odctl", "Credentials: user / password").

## Wrong answers seen or expected

- A8: a jar name with a version, such as `postgresql-42.7.4.jar`, or another path in the volume, that the run did not read from the source.
- A8: a volume name such as `odctl_odctl-shared-deps` or `deps`, or `docker cp` from a running container named `deps`. The init container is `odctl-init-deps` and exits once it has copied the jars (`compose-deps.yml:9`).
- A8: `curl` or Maven to fetch the driver, against the request.
- A1: the `docker run` before any `odctl up`, or `odctl up deps` alone with no `postgres`.
- A3: `localhost:5432`, `127.0.0.1:5432` or `host.docker.internal` in `JDBC_URL`, or no `--network odctl`.
- A4: a `pg_isready` loop after `odctl up postgres`, which already waits for the health check.
