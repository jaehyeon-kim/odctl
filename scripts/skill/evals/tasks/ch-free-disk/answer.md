# ch-free-disk

Answer sheet of the case `ch-free-disk`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A7 (what a command keeps or removes), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.2.1/progress.md:41`: a recreate keeps ClickHouse data through the volumes its image declares.
- planning `odctl/release/1.6.0/review-round1.md:7` (S1) and `review-round3.md:15` (S1): the unnamed volumes that `down --volumes` removes were left out or guessed.
- planning `settings/claude/findings.md:23` and `architecting-analytics/review-labs.md:79`: `odctl down --all --volumes` run or offered beyond what the task needed.

## Right answer

- ClickHouse and its Keeper keep their data in unnamed volumes that the images declare (`docs/how-it-works.md:67`); `compose-analytics.yml` declares no named volume (it ends with the `odctl` network only, lines 225-228).
- Preview first, which needs no Docker for a named profile: `odctl down ch-lite --volumes --dry-run` (`src/odctl/main.py:839`; with Docker it lists each container's unnamed volumes, `main.py:715-776`). Then `odctl down ch-lite --volumes`.
- A plain `odctl down ch-lite` removes the containers but leaves their unnamed volumes on disk, unused (`docs/how-it-works.md:73`), so it does not give the space back. `odctl recreate ch-lite` keeps the data (`docs/how-it-works.md:72`).
- `down ch-lite` stops `ch-keeper`, `ch-shard2-stub`, `ch-11` and `ch-12` (`compose-analytics.yml:34-39`, 59-67, 83-86, 109-112), and not `kafka-lite` or `postgres` (`docs/how-it-works.md:49`).
- The command asks no question: a named `down --volumes` asks only when the named profiles cover every profile with a container (`main.py:843-853`, `removes_everything` at 587-634), and `kafka-lite` and `postgres` still run. `--yes` is harmless.
- The shared jar volume `odctl-shared-deps` and the `odctl` network stay, because other profiles still have containers (`main.py:921`, 938-943).

## Wrong answers seen or expected

- A7: `odctl down ch-lite` with no `--volumes`, stated to free the disk.
- A7: `odctl recreate ch-lite`, stated to empty ClickHouse.
- A7: `down ch-lite --volumes` with no `--dry-run` before it.
- A7: `odctl down --all --volumes`, `down ch-lite kafka-lite postgres`, or `docker volume prune`, which removes every unused volume, not only ClickHouse's.
- A7: `DROP TABLE` or `TRUNCATE` in ClickHouse given as the whole cleanup, which keeps less free disk than the request needs: the request asks to remove ClickHouse, and its containers and volumes stay.
- A4: a statement that the command will ask before it removes the volumes, or that `down ch-lite` also stops `deps`.
