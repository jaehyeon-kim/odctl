# teardown-keep-pg

Answer sheet of the case `teardown-keep-pg`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A7 (what a command keeps or removes), A4 (odctl CLI behaviour assumed).

## Records

- planning `settings/claude/findings.md:29-31` and `architecting-analytics/review-labs.md:79`: `odctl down --all --volumes` run or offered beyond what the task started.
- planning `odctl/release/1.6.0/review-round1.md:7` and `:8`, `review-round3.md:15`: the unnamed volumes `down --volumes` removes were left out or guessed.

## Right answer

- Preview first, which needs no Docker: `odctl down kafka-lite --volumes --dry-run` (`docs/snippets/getting-started/commands.sh:82`). With Docker it lists each container's unnamed volumes (`main.py:589-602`).
- Then `odctl down kafka-lite`, with `--volumes` to remove the anonymous volumes the `apache/kafka` image declares (`docs/how-it-works.md:67`); without it they stay on disk, unused.
- `down kafka-lite` stops `compose-kafka.yml` only. The shared network and jar volume go only when no other profile has a container (`main.py:690-699`), so a running `postgres` keeps them.
- A named `down <profile> --volumes` asks no question; only `down --all --volumes` asks (`main.py:669-673`).
- PostgreSQL keeps its data in an unnamed volume the `postgres` image declares (`compose-infra.yml:48-49` mounts only the init script), so any `odctl down postgres` loses it (`docs/how-it-works.md:69-74`).

## Wrong answers seen or expected

- `odctl down --all`, with or without `--volumes`.
- `odctl down kafka-lite postgres`.
- Saying the command will ask before it removes volumes.
- Saying PostgreSQL has a named data volume that survives `down postgres`.
