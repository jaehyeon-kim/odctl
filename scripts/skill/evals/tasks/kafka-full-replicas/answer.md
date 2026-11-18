# kafka-full-replicas

Answer sheet of the case `kafka-full-replicas`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A2 (service called before it is ready), A10 (a check that cannot fail), A12 (a number given with no reason).

## Records

- github `jaehyeon-kim/odctl#20`: a user connected to `localhost:29092`, a port Kafka advertised only for minikube (A3).
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit (A2).
- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1): a Kafka check whose `grep` also matched `delete.retention.ms`, so it could not fail (A10).
- A12 has no odctl record; this case extends the evidence of `planning/odctl/plan-agent-skill.md:30` (a wait limit an agent picks).

## Right answer

- `odctl up kafka-full` (`registry.yml:68-71`; `odctl up kafka-full --dry-run` starts `deps` and `kafka-full`).
- From the host the bootstrap servers are `127.0.0.1:9092,127.0.0.1:9093,127.0.0.1:9094` (`registry.yml:90`; `docs/guides/kafka.md:15`). Each broker advertises its own host port on the external listener (`compose-kafka.yml:81`, `102`, `123`), so one of them is enough to bootstrap and listing all three is also right.
- The brokers have no health check (`compose-kafka.yml:67-128`), and `odctl up` runs `docker compose up --wait` (`src/odctl/docker.py:482`), which waits for health checks or, without one, for the container to run. So `up` can return before the three brokers have registered. Creating a topic with replication factor 3 before then fails with `InvalidReplicationFactorException`, "The target replication factor of 3 cannot be reached because only N broker(s) are registered" (apache/kafka tag `4.3.2`, `metadata/src/main/java/org/apache/kafka/metadata/placement/StripedReplicaPlacer.java:411-416`; the image is `apache/kafka:4.3.2`, `compose-kafka.yml:32`). The script, or `run.sh`, waits until the cluster reports three brokers (`AdminClient.list_topics().brokers` or `describe_cluster()`), with a limit; odctl's own test retries 30 times at 5 seconds until a broker answers (`.github/scripts/smoke.sh:212-213`).
- The topic: `NewTopic("payments", num_partitions=6, replication_factor=3, config={"min.insync.replicas": "2"})`. The brokers' default replication factor on `kafka-full` is already 3 (`compose-kafka.yml:84`), so leaving `replication_factor` out also gives 3; `min.insync.replicas` is not set by odctl, so the topic must set it.
- The producer uses `acks=all` and checks each delivery report or the result of `flush()`, so a failed write is not reported as written.
- The check reads the topic as it is after the writes: `list_topics(topic="payments")` or `describe_topics`, and exits 1 unless each of the 6 partitions has 3 entries in `isrs` (and 3 in `replicas`). A check that reads only the arguments it passed to the create call, or only the create call's success, passes when replicas are out of sync, so it cannot fail.
- Each number the script picks has its reason beside it: the wait's limit and interval.

## Wrong answers seen or expected

- A3: `broker-1:19092`, `kafka-1:19092`, `kafka:9092` or any port 29092 from the host; `broker-1` and the `kafka-*` names resolve only inside the `odctl` network (`compose-kafka.yml:74-76`).
- A3: `docker exec kafka ...` for a Kafka tool: `kafka-full` has no container named `kafka`; the tools are in `kafka-1` (`docs/guides/kafka.md:23`).
- A2: creating the topic straight after `odctl up`, or after a fixed `sleep` with no check of the broker count, or a wait with no limit.
- A10: a check that passes without reading the in-sync replicas of the topic on the brokers.
- A12: a wait limit, a retry count or a `sleep` with no reason given.
