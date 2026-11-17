# CI step: start kafka-lite + postgres and wait for Kafka

I wrote `ci_start.sh`. **I have not run it.** Docker isn't available on this machine, so I only checked that it parses (`bash -n`) and that `odctl up kafka-lite postgres --dry-run` gives the expected plan.

## What `ci_start.sh` does
1. Runs `py/bin/odctl up kafka-lite postgres`. This returns once the services are running, and healthy where they have a health check.
2. Creates a topic with a unique name per run, using `docker exec kafka` and the Kafka CLI tools, retrying until the broker answers.
3. Produces one message to that topic.
4. Reads the message back with a consumer group, `--from-beginning --max-messages 1`. It retries until the message comes back or `WAIT_SECS` (default 180) runs out. This is the check that the tests can start.
5. On success it exits 0. On a timeout or error it prints `odctl ps` and the Kafka logs and exits non-zero.
6. On the way out it deletes the test topic.

Postgres is only covered by `odctl up`'s own health wait. The script does not run a separate Postgres query check.

## Before you run it
- **Docker is needed on the CI runner.** The script calls `docker exec` directly, not only `odctl`.
- It uses the container name `kafka` and Kafka's tools in `/opt/kafka/bin`. I took both from odctl's `compose-kafka.yml` and the `apache/kafka` image, so check them against the real container on the first run. If odctl renames the container, the script breaks.
- It runs odctl as `py/bin/odctl`, relative to the working directory. Run it from the repo root, or set `ODCTL=/path/to/odctl`.
- `WAIT_SECS` sets the time budget for the Kafka check. It does not cover `odctl up` itself, including the image pulls.
- The topic and group names include the timestamp and PID, so reruns on a reused runner don't see old messages.
- The script checks Kafka from inside the broker container (`localhost:9092`). It does not test the host port `127.0.0.1:9092` that your tests will connect to. If the tests run on the host, add a check from there.
- `odctl down` is not called, so add your own teardown.
