# Reply: kafka-lite teardown

I wrote `teardown.sh` in this folder. I did not run it: Docker is not available on this machine, so I could not stop anything or confirm the result.

## What the files do

**`teardown.sh`** (executable bash script)

1. Finds `py/bin/odctl` and `.odctl/` relative to its own location, so it works from any directory. It exits if either is missing.
2. Prints the plan with `odctl down kafka-lite --volumes --dry-run`.
3. Runs `odctl down kafka-lite --volumes --yes`. This stops the kafka-lite profile, removes its containers, removes the unnamed volumes of those containers, and passes `--yes` so the confirmation prompt does not block a script.
4. Runs `odctl ps` so you can see what is still running.

It does not use `--all`, does not name `postgres`, and does not stop `kafka-full`.

## What you must know before running it

- **PostgreSQL is not touched by the script.** Its data is in its own container, and it is not in the kafka-lite profile. But `odctl ps` at the end is the only check: confirm `postgres` is still listed.
- **Shared volume and `deps`.** kafka-lite depends on the `deps` profile. The dry-run says odctl will stop `deps` and remove the shared volume `odctl-shared-deps` only if no other profile has a container. PostgreSQL has a container, so odctl should keep both. I could not verify this because Docker is unreachable here. If that guard does not hold on your machine, the shared JAR volume would be removed, which affects the catalog, Flink and Spark profiles, not PostgreSQL's data.
- **Kafka data is lost.** Kafka keeps its data in the container layer, so `--volumes` removes what the test wrote. That is what a finished test needs, but do not run the script if you still need the topics.
- **Docker must be running.** The script fails if Docker is down; `odctl` reports "Docker is not reachable" and nothing is removed.
- **Run it once.** A second run finds nothing to stop and should be harmless, but it is not tested here.

## Not verified

I ran only a syntax check (`bash -n`) and an `odctl down kafka-lite --volumes --dry-run`. The dry-run could not check Docker state, so its output shows the plan, not what exists. I did not run the real teardown.
