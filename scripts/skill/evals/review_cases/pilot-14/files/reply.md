# Teardown for the kafka-lite test

I wrote one script, `teardown.sh`, and this note.

## What `teardown.sh` does

Run it from anywhere with `bash teardown.sh`. It switches to its own folder, so it uses the `.odctl/` workspace and `py/bin/odctl` there.

1. `odctl down kafka-lite --volumes --dry-run` prints the plan and changes nothing.
2. `odctl down kafka-lite --volumes --yes` stops and removes the four kafka-lite containers (`kafka`, `connect`, `karapace`, `kafka-ui`) and the volumes those containers used. `--yes` skips the confirmation prompt.
3. `odctl ps` lists what is still running. `postgres` should be in the list.

## Why PostgreSQL and its data are safe

- `odctl down` stops only the profiles you name. It does not stop their dependencies. The script names only `kafka-lite`, so the `postgres` container is not touched.
- `--volumes` removes only the volumes of containers that get stopped. Postgres keeps running, so its data is not removed.
- `odctl up kafka-lite` also started `deps`, which is the shared jar volume `odctl-shared-deps` plus the `odctl` network. Postgres needs `deps` too, and `deps` was already running before the test. odctl keeps `deps` and `odctl-shared-deps` while another profile has a container, and the dry-run plan says so: "only if no other profile has a container". Postgres has one, so both stay.

## Before you run it

- **I could not test it here.** Docker isn't available on this machine. The dry-run ran, but without Docker odctl could not check which containers and volumes actually exist. Check the step 1 output on your machine before step 2 runs. If you'd like to stop and read it first, run `py/bin/odctl down kafka-lite --volumes --dry-run` by hand.
- **Kafka data is deleted for good.** All topics, messages, schemas in Karapace and Connect state are lost. Keep anything you need from the test before you run the script.
- **If the volume removal feels risky, leave out `--volumes`.** The containers are still removed and Kafka's data still goes with them. Only the leftover unnamed volumes stay on disk, unused. The postgres situation is the same either way.
- Never use `odctl down --all` or `odctl down postgres` for this. Either one would stop PostgreSQL, and its data would be lost.
