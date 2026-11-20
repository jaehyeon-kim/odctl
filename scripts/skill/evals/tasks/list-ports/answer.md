# list-ports

Answer sheet of the case `list-ports`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.8.0/reader-check.md:21`, `architecting-analytics/validation-live-stack.md:183`: `odctl ps` with no profile exits 1 asking for profile names or `--all` (`planner.py:162-164`).
- planning `odctl/release/1.5.0/reader-check.md:5`: `ps --json` needs profile names or `--all`.

## Right answer

- `odctl ps --all --json`: one object with host and container ports as numbers, and health `null` where a service has no health check (`docs/getting-started.md:290-292`; `docs/snippets/getting-started/commands.sh:54-64`).
- It needs Docker; `odctl list -d` and `odctl explain <profile>` give declared ports without Docker.

## Wrong answers seen or expected

- `odctl ps` or `odctl ps --json` with no profile and no `--all`.
- `docker ps` in place of odctl's command, or a parse of the table output.
