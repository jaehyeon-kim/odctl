# ci-consumer-wait

Answer sheet of the case `ci-consumer-wait`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A2 (service called before it is ready), A4 (odctl CLI behaviour assumed), A12 (a number with no reason).

## Records

- planning `odctl/release/1.4.0/review-batch2-round1.md:12`: an extra readiness probe after `odctl up` for a service whose health check `up` already waits for.
- planning `odctl/release/1.4.0/audit.md:12`: a wait with no limit.
- planning `odctl/release/1.4.0/review-batch1-round3.md:21`: a fixed wait of a few seconds, replaced by a repeat until success.

## Right answer

- `odctl up kafka-lite postgres`. `up` returns when services are running, and healthy only where they have a health check (`docker.py:456-458`; `docs/how-it-works.md:34`).
- `postgres` has a health check (`compose-infra.yml:52-57`), so no extra wait for it is needed.
- `kafka`, `connect` and `kafka-ui` have no health check (`compose-kafka.yml`; `docs/getting-started.md:276-282`), so `up` returning does not mean Kafka answers.
- Wait for Kafka with a limit, repeating a call that needs the broker: `docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 --list` under a retry with a count and a delay (`smoke.sh` `guide_kafka`, lines 188 and 189).
- Then show that a consumer group reads: produce one message and consume it with `kafka-console-consumer.sh --group <name> --from-beginning --max-messages 1 --timeout-ms <limit>` (`docs/snippets/kafka/commands.sh` `produce-consume`, lines 14 to 21; `smoke.sh:192-196`). A group read needs the group coordinator, which a read with `--partition` skips.
- Each retry count, delay and timeout carries its reason.

## Wrong answers seen or expected

- Treating the exit of `odctl up` as Kafka being ready.
- A loop with no limit, or a fixed `sleep`.
- An extra `pg_isready` loop after `up`.
- A read with `--partition` or assign mode, which does not test a consumer group.
- `localhost:9092` in a container other than `kafka`. Inside the `kafka` container of `kafka-lite` it works, and is not A3, while `DOCKER_HOST_IP` is unset, the default, because the broker listens on `0.0.0.0:9092` and advertises `127.0.0.1:9092` (`compose-kafka.yml:48-49`). With `DOCKER_HOST_IP` set, the broker advertises that address instead, which the container may not reach, so `broker-1:19092` is the address the skill gives.
