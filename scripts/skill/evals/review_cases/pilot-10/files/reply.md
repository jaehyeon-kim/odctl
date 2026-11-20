I wrote `teardown.sh` (one command) and this file. I couldn't run the script here because Docker isn't available. I did run `odctl down kafka-lite --dry-run` and it planned to stop only `kafka-lite`.

**`teardown.sh`** runs `odctl --workspace .odctl down kafka-lite --yes`, using the `py/bin/odctl` and `.odctl/` next to the script. Run it with `bash teardown.sh`. It works from any directory.

Things to know before you run it:
- **PostgreSQL is untouched.** The script names only `kafka-lite`. It leaves out `--all` and `--volumes`. `--volumes` would also remove the shared `odctl-shared-deps` volume once no other profile has a container. Postgres still has one, so that wouldn't happen, but I kept the script minimal.
- **The `deps` profile stays up.** `odctl up kafka-lite` also started `deps`, which postgres shares. `down kafka-lite` doesn't stop dependencies.
- **Kafka data is lost.** `down` removes the broker, connect, karapace and kafka-ui containers, and any topics or messages kept inside them go with them. The profile has no named volumes.
- **The prompt is skipped.** `--yes` answers odctl's confirmation, so the script won't ask.
- **Check afterwards.** `py/bin/odctl ps` should show postgres still running.
