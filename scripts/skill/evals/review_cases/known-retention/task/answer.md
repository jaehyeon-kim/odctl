# kafka-retention-check

Answer sheet of the case `kafka-retention-check`, written from odctl <version>'s sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v<version>`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A10 (a check that cannot fail), A3 (address from the wrong side).

## Records

- planning `odctl/release/1.2.0/review-batch1.md:11`: `grep -q 'retention.ms=86400000'` also matched `delete.retention.ms=86400000`, so the check could not fail.

## Right answer

- `docker exec kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server broker-1:19092 --describe --all --entity-type topics --entity-name events` (`docs/snippets/kafka/commands.sh` `retention-default`, lines 22 to 25).
- Match the key exactly: `grep -Eq '^ *retention\.ms=86400000 '`, anchored so that `delete.retention.ms` cannot match (`smoke.sh:200`).
- `--all` shows the broker default for a topic with no override (`smoke.sh:197`); the broker default is `KAFKA_LOG_RETENTION_MS: "86400000"` (`compose-kafka.yml:13`).
- The check is shown to fail: for example against a topic set to another retention.

## Wrong answers seen or expected

- An unanchored `grep retention.ms=86400000`.
- `--describe` without `--all` on a topic with no override, which prints no `retention.ms`.
- `kafka-configs` without the path and `.sh`.
- `localhost:9092` inside the container.
