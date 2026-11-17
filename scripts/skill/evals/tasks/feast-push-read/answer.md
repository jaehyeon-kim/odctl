# feast-push-read

Answer sheet of the case `feast-push-read`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A1 (a step needs an earlier step), A3 (address from the wrong side), A2 (service called before it is ready).

## Records

- planning `odctl/release/1.4.0/reader-check.md:9`, `:10`: a step run before the step it needs.
- planning `odctl/release/1.4.0/review-batch1-round1.md:10`: the apply was skipped, so the push was rejected.

## Right answer

- `odctl up feast` (depends on `catalog` and `valkey`, `registry.yml:243`).
- Apply the push source inside the server first: `docker cp push_definitions.py feast-serve:/tmp/feature_repo/push_definitions.py`, then `docker exec feast-serve feast -c /tmp/feature_repo apply --skip-source-validation` (`docs/snippets/feast-iceberg/commands.sh` `push-apply`, lines 51 to 54; `docs/guides/feast-iceberg.md:239-297`).
- Push: `POST http://127.0.0.1:6566/push` with `push_source_name`, `allow_registry_cache: false`, `to: online` and a new `event_timestamp` (`push-http`, lines 56 to 63).
- Read: `POST http://127.0.0.1:6566/get-online-features` (`push-read`, lines 73 to 77). The server's registry cache can lag the apply by up to a minute, so the read is repeated with a limit (`smoke.sh:1894-1912`).

## Wrong answers seen or expected

- Pushing before the apply, or applying only to a repository on the host that the server does not serve.
- `feast-serve:6566` from the host.
- A first read that says the view does not exist taken as a failure, with no repeat.
- Pushing with the timestamp of the stored value, which does not replace it.
