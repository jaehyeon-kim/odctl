# feast-serve-repo

Answer sheet of the case `feast-serve-repo`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side, or guessed), A2 (service called before it is ready), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): the guide told the reader to put a host address into a repository for the services; the services need container addresses.
- planning `odctl/release/1.7.0/review-round1.md:7`: healthy containers taken to mean the function works.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit.
- A12 has no odctl record; this case extends the evidence of desflow's K14 that `plan-agent-skill.md`, Kinds of mistake, row A12, cites.

## Right answer

- The feature server does not read the registry project the laptop applied until it is given the repository: it loads its repository from `s3://feast/repo`, and with that prefix empty it loads the bundled one (`src/odctl/resources/compose-mlops.yml:37-53`), whose project is `odctl`, not `demo` (`src/odctl/resources/feast/feature_store.yaml:13`). So `serve_repo.sh` uploads the repository to `s3://feast/repo` (`src/odctl/resources/registry.yml:263-265`; `docs/guides/feast-iceberg.md:233`).
- The uploaded `feature_store.yaml` must use the container addresses, `postgres:5432` for the registry and `valkey:6379` for the online store, because the services run inside the `odctl` network (`docs/guides/feast-iceberg.md:233`, 391). The laptop's `feature_repo/feature_store.yaml` has `127.0.0.1` addresses (the case's `setup.sh`), so the script uploads a copy with those two lines changed and keeps the laptop's file as it is, since the laptop's own `feast` commands need it. `definitions.py` needs no change (`docs/guides/feast-iceberg.md:233`).
- The upload works from the host to `http://127.0.0.1:8333` with key `user` and secret `password` (`registry.yml:47-50`), or with boto3 inside a Feast container, whose start-up script already uses it with `http://seaweed:8333` and the container's AWS keys (`compose-mlops.yml:29-31`, 39-41). The keys are `repo/feature_store.yaml` and `repo/definitions.py` in the bucket `feast` (`compose-mlops.yml:43-52`).
- The services list the prefix every 15 seconds and restart Feast when it changes (`compose-mlops.yml:70-82`; `registry.yml:263-264`). `/health` answers on the bundled repository before that (`compose-mlops.yml:249-250`), so it does not show that the features are served. `read_feature.py` sends `POST http://127.0.0.1:6566/get-online-features` with `{"features": ["driver_stats:conv_rate"], "entities": {"driver_id": [1001]}}` (`registry.yml:270-272`; `docs/guides/feast-iceberg.md:291-295`) and prints the value, and when the steps read after the upload, they wait for that read to return a value, retrying with a limit that covers the 15-second check and the restart, with the reason beside it. The script exits 1 when the answer is an error or the value is null.
- The profile must be running (`odctl up feast`); the request says it is, so starting it again is not counted.

## Wrong answers seen or expected

- A3: uploading the laptop's `feature_store.yaml` unchanged; `http://feast-serve:6566` or `seaweed:8333` in code that runs on the laptop.
- A6: a read through the SDK with `repo_path` in place of the feature server, which reads the store directly and does not show the server serves the features.
- A3: an edit of the laptop's `feature_repo/feature_store.yaml` to container addresses, which breaks the laptop's own `feast` commands, with no warning.
- A2: a read straight after the upload, or a wait on `/health` taken to mean the new repository is loaded.
- A12: a retry count, interval or timeout with no reason beside it.
- A2: a wait with no limit.
