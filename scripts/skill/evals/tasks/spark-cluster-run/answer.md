# spark-cluster-run

Answer sheet of the case `spark-cluster-run`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (stack setting assumed), A2 (service called before it is ready), A10 (a check that cannot fail), A12 (a number given with no reason).

## Records

- planning `architecting-analytics/validation-live-stack.md:146` and `odctl/release/1.2.0/review-batch1.md:12` (R1 2): what the Spark image and its settings hold was assumed (A8).
- planning `odctl/release/1.7.0/review-round1.md:7` (A-S1) and `odctl/release/1.4.0/review-batch1-round3.md:21`: running containers taken to mean the service can do the work (A2).
- planning `odctl/release/1.4.0/audit.md:11` (M1): a check that hid its own failure (A10).
- A12 extends the evidence of `planning/odctl/plan-agent-skill.md:30`.

## Right answer

- `odctl up spark-full` (`registry.yml:122`).
- Only `spark-master` has a health check (`compose-spark.yml:33-37`); the workers have none and start once the master is healthy (`compose-spark.yml:39-73`). `odctl up` waits for health checks or running containers (`src/odctl/docker.py:482`), so it can return before the workers have registered. The wait asks the master: `http://127.0.0.1:9080/json/` from the host (`compose-spark.yml:30`), or `http://spark-master:8080/json/` inside the network, until `aliveworkers` is 3 (apache/spark tag `v4.1.4`, `core/src/main/scala/org/apache/spark/deploy/JsonProtocol.scala:229`; the master page is at the root, and `ui/WebUI.scala:97` adds `/json` to each page), with a limit and its reason.
- `spark-defaults.conf` sets no `spark.master` (the whole file), and the image sets no `MASTER` variable (apache/spark-docker `4.1.4/scala2.13-java21-ubuntu/Dockerfile`, its only `ENV` lines are 39 and 75; the odctl image adds none, `docker/spark/Dockerfile`). `spark-submit` with no `--master` therefore runs `local[*]` inside the container it is started in (`SparkSubmitArguments.scala:44-47`, `163-165`); `docs/guides/spark.md:41` shows such a run's event log, `eventlog_v2_local-...`. The run: `docker cp count_words.py spark-master:/tmp/` then `docker exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /tmp/count_words.py` (`registry.yml:142`; `docs/guides/spark.md:140`).
- The check asks the master which applications ran: `completedapps` in `http://127.0.0.1:9080/json/` (`JsonProtocol.scala:238`, with `name`, `starttime`, `cores` and `state`, lines 101-115), and exits 1 unless the latest entry is `count-words` (the name the job sets) with state `FINISHED`. A job run in local mode never registers with the master, so it is missing there. Reading the History Server at `http://127.0.0.1:18080/api/v1/applications` and checking that the latest `count-words` id starts with `app-`, not `local-`, is also right.
- A check that relies on `spark-submit`'s exit code or on the printed counts passes for a local run too, so it cannot fail on the thing asked.

## Wrong answers seen or expected

- A8: `spark-submit` with no `--master`, described as running on the workers.
- A3 (counted, not a kind of this case's focus): `--master spark://127.0.0.1:7077` inside the container, or `spark://localhost:7077`; the master binds `spark-master` (`compose-spark.yml:28`).
- A2: running the job straight after `odctl up`, or a fixed `sleep` with no check of the workers, or a wait with no limit.
- A10: a check that passes on the exit code, the output, or the master UI answering, without finding the run among the master's applications.
- A12: a wait limit or interval with no reason.
