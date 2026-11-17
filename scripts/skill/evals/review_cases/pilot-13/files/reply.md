# CI startup step for kafka-lite and postgres

I wrote `ci_start.sh`, the CI step. It starts both profiles. It finishes only after Postgres answers a query and a Kafka consumer group has read a message that the script itself produced. If either is not ready in time, it prints the container logs and exits with a non-zero status, so the job stops before your tests run.

**It has not been run.** Docker is not available on this machine. I checked the bash syntax with `bash -n`, and the script uses the container names, listeners and tool paths from odctl's own compose files. Watch the first CI run.

## Why the script does its own waiting

`odctl up` returns when the containers are running, and healthy where they have a health check. The Postgres container has one. The Kafka broker in `kafka-lite` does not, so `odctl up` can return before Kafka is ready to serve consumer groups: the group coordinator and the `__consumer_offsets` topic come up later. Tests that run straight after `odctl up` can fail now and then for that reason.

## What `ci_start.sh` does

1. **Starts the profiles** with `odctl up kafka-lite postgres`. This also starts `deps`, which both profiles depend on.
2. **Checks Postgres:** it runs `psql -U user -d odctl -c 'SELECT 1'` inside the `postgres` container until the query succeeds.
3. **Checks Kafka,** retrying until all of these steps succeed, using the Kafka tools inside the `kafka` container:
   - creates a topic for this run: `ci-readiness-<run id>`, with 1 partition and replication factor 1;
   - produces a marker message with `acks=all`;
   - reads it back with `kafka-console-consumer --group <new group> --from-beginning --max-messages 1`;
   - runs `kafka-consumer-groups --describe` to confirm the group exists with a committed offset.
4. **Cleans up** by deleting the test topic, then prints the connection details: Kafka at `127.0.0.1:9092`, and Postgres at `postgresql://user:password@127.0.0.1:5432/odctl`.

Each run uses its own topic, group and marker, so data left over from an earlier run cannot make the check pass by mistake.

## Before you run it

- **Requirements on the runner:** Docker, and odctl version 1.x. The script uses `./py/bin/odctl` if it exists next to the script, and otherwise `odctl` from `PATH`. To use a different one, set `ODCTL=/path/to/odctl`. You don't need to install any Kafka or Postgres client tools, because the checks run inside the containers with `docker exec`.
- **Free ports:** odctl binds these on `127.0.0.1`, and nothing else on the runner can be using them: 9092 (Kafka), 8081 (Karapace), 8083 (Connect), 8086 (Kafka UI) and 5432 (Postgres). Note that `kafka-lite` also starts Connect, Karapace and Kafka UI.
- **Memory:** the memory limits add up to about 5.5 GB. Connect alone is allowed 2 GB.
- **Timeouts:** `READY_TIMEOUT` (default 180 seconds) applies only to the waiting after `odctl up` returns. Pulling the images on a fresh runner happens inside `odctl up` and is not counted, so leave the CI job extra time for it, or run `odctl pull` in a cached step first. `ATTEMPT_TIMEOUT_MS` (default 10000) sets how long each read attempt waits for the message.
- **Shutting down:** the script does not stop anything. If your runners are not thrown away after each job, add a final step that always runs: `odctl down --all --volumes --yes`. `down` deletes all data held in the containers.
- **Use from containers:** the tests reach the services from the host at `127.0.0.1`. If your tests run in a container instead, it must join the `odctl` Docker network and use `broker-1:19092` and `postgres:5432`.
