# host-iceberg-trino

Answer sheet of the case `host-iceberg-trino`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side, or guessed), A1 (a step needs an earlier step), A4 (odctl CLI behaviour assumed).

## Records

- planning `architecting-analytics/review-labs.md:39`, `:44`: `iceberg-rest:8181`, `seaweedfs:8333`, `storage:8333` and `admin/admin`, which do not exist.
- planning `architecting-analytics/review-labs.md:43`: `odctl trino` written as a command.
- planning `architecting-analytics/review-labs.md:159`: `odctl up trino` assumed to start `catalog` and `storage`.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5`: the container address `catalog:8181` used from the host.

## Right answer

- `odctl up catalog trino`: `trino` alone starts `deps`, `postgres` and `trino` (`registry.yml:176`), and its Iceberg catalog fails at query time unless `catalog` and `storage` are up (`registry.yml:197-200`); `catalog` brings `postgres` and `storage` (`registry.yml:58`).
- From the host: REST catalog `http://127.0.0.1:8181` (`registry.yml:62`); S3 `http://127.0.0.1:8333` with keys `user` and `password` (`registry.yml:47-49`); warehouse `s3://warehouse/`, path-style access, region `us-east-1` (`docs/snippets/feast-iceberg/commands.sh` `catalog-env`, lines 17 to 24).
- Trino from the host: `http://127.0.0.1:8080`, no password, any user name (`registry.yml:188-196`); or `docker exec trino trino --execute '...'` (`docs/snippets/trino-metabase/commands.sh:14`).

## Wrong answers seen or expected

- `catalog:8181`, `iceberg-rest:8181`, `iceberg-catalog:8181` or `seaweed:8333` from the host.
- `admin/admin` or any login not in the notes.
- `odctl trino`, or `docker exec -it trino trino` in a script (the `-t` needs a terminal; `registry.yml:193`).
- `odctl up trino` alone.
