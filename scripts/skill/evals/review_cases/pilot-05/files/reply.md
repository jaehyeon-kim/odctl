# CI step: start kafka-lite and postgres, wait for Kafka

## What I wrote

- **`ci_start.sh`** (executable bash script, in this folder). It:
  1. Runs `py/bin/odctl up kafka-lite postgres`. The profile list is the two profiles you named; `deps` starts automatically as a dependency.
  2. Waits for Postgres with `pg_isready` in the `postgres` container, for up to `CI_READY_TIMEOUT` seconds (default 240).
  3. Probes Kafka with a real consumer group. Each attempt creates the topic `odctl-ci-probe` if needed, produces a unique token, then reads the topic with a brand-new consumer group (`--from-beginning`, 10 s idle timeout). The step passes only when the consumer prints that exact token. It retries every 3 s until the deadline, then dumps the last 80 lines of the `kafka` container log and exits 1.
  4. Exits 0 once the probe succeeds, so the tests after it start only when a consumer group can read a message.
- **`reply.md`**: this file.

## What you must know before running it

- **I did not run it.** Docker is not available on this machine, and `odctl up ... --dry-run` fails with "Docker is not reachable". I checked only the bash syntax (`bash -n` passes). The Kafka probe commands are untested.
- **Assumptions I could not verify here:**
  - The `kafka` container has the Kafka CLI tools at `/opt/kafka/bin` (the standard `apache/kafka` image layout).
  - The internal listener `kafka:19092` is reachable from inside that container. It comes from `compose-kafka.yml`, where `KAFKA_LISTENERS` binds it.
  - The `postgres` container accepts `pg_isready -U user -d odctl`. I took the user and database from the profile notes.
- **Container names matter.** The script uses `docker exec` on the containers `kafka` and `postgres`. The CI runner needs the Docker CLI and access to the Docker daemon.
- **`odctl up` returns before Kafka is usable.** `kafka-lite` has no healthcheck, which is why the probe exists. Don't remove it.
- **Side effects on the broker:**
  - Each attempt leaves a consumer group named `ci-ready-probe-...` behind. They are harmless but accumulate across runs.
  - The `odctl-ci-probe` topic grows by one token per attempt. Use `CI_PROBE_TOPIC` to change the topic name.
- **Timing:** a successful probe takes roughly 10 s, because the consumer waits out its idle timeout. A failed Kafka start takes up to `CI_READY_TIMEOUT` seconds before the step fails.
- **Working directory:** the script `cd`s to its own folder, and it uses `py/bin/odctl` there. Override with `ODCTL_BIN` if the CI layout differs. Because `odctl` writes a `.odctl/` workspace in the current directory, run the script from the project root that should own it.
- **Nothing else was changed.** I wrote only `ci_start.sh` and `reply.md`, and I did not install anything.
