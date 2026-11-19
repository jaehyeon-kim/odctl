# ci-flink-slots

Answer sheet of the case `ci-flink-slots`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A2 (service called before it is ready), A3 (address from the wrong side), A8 (stack setting assumed), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.7.0/review-round1.md:7` (A-S1) and `odctl/release/1.4.0/review-batch1-round3.md:5` (S1): healthy or started taken to mean ready for the work (A2).
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): a container address used from the host (A3).
- planning `architecting-analytics/validation-live-stack.md:143` and `:147`: a service setting assumed instead of read (A8).
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit (A2).

## Right answer

- `odctl up flink-full kafka-lite` (`registry.yml:70`, `99`).
- `flink-full` runs three TaskManagers (`compose-flink.yml:55-83`), each with 5 task slots (`flink/flink-conf.yml:8`), so 15 slots. "A Flink cluster needs exactly as many task slots as the highest parallelism used in the job" (Flink 2.2 docs, Flink Architecture), so a job of parallelism 12 needs 12 free slots, which only all three TaskManagers together give.
- Only the JobManager has a health check (`compose-flink.yml:49-53`); the TaskManagers have none and start once it is healthy (`compose-flink.yml:61-63`). `odctl up` waits for health checks or running containers (`src/odctl/docker.py:482`), so it can return before the TaskManagers have registered.
- The wait asks the JobManager from the CI host: `http://127.0.0.1:8082/overview` (`compose-flink.yml:47`; `registry.yml:111`; path `/overview`, apache/flink `release-2.2.0`, `ClusterOverviewHeaders.java:34`), until `slots-available` is at least 12 (`ClusterOverview.java:38-40`), with a limit and its reason, and the step exits 1 when the limit passes.

## Wrong answers seen or expected

- A3: `http://127.0.0.1:8081` from the host, which is Karapace when `kafka-lite` runs (`compose-kafka.yml:196`); `http://jobmanager:8081` or `flink-jobmanager:8081` from the host.
- A8: a statement that each TaskManager has one slot, so 12 slots cannot be reached or need 12 TaskManagers; a change of `taskmanager.numberOfTaskSlots` or of the TaskManager count described as needed.
- A2: no wait after `odctl up`; a wait on `/config`, the health check, the container state or the `taskmanagers` count only, because only `slots-available` shows that 12 slots are free; a fixed `sleep`; a wait with no limit.
- A12: a wait limit or interval with no reason.
