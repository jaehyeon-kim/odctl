# mlflow-serve-new-version

Answer sheet of the case `mlflow-serve-new-version`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A2 (service called before it is ready), A3 (address from the wrong side, or guessed), A6 (service behaviour stated without a run or its source), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.8.0/reader-check.md:16`: after `odctl restart telemetry` the first request got "Service Unavailable"; a restarted service is not ready when the command returns.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit.
- planning `odctl/release/1.4.0/review-batch1-round2.md:7` (S3): a service's behaviour stated from memory, here what the model server does when an alias moves.
- A12 has no odctl record; this case extends the evidence of desflow's K14 (a number with no reason) that `plan-agent-skill.md`, Kinds of mistake, row A12, cites.

## Right answer

- Inside the `odctl` network the tracking server is `http://mlflow:5000` and the model server `http://mlflow-serve:5003` (`src/odctl/resources/registry.yml:251`, 257; `docs/guides/mlflow.md:20`, 22, 207). `register_version.py` sets the tracking URI to `http://mlflow:5000` (or reads `MLFLOW_TRACKING_URI`, with that value named in the reply), registers `runs:/<RUN_ID>/model` as `churn-model` and points `champion` at the version that call returns (`docs/guides/mlflow.md:62-77`). `mlflow:5000` is in `--allowed-hosts` (`src/odctl/resources/compose-mlops.yml:148`), and artifacts go through the server, so the job needs no S3 settings (`docs/guides/mlflow.md:52`).
- Moving the alias does not change what is served: `mlflow-serve` resolves `MODEL_URI` once, when its container starts, and nothing reports an error in the meantime (`registry.yml:253-255`; `docs/guides/mlflow.md:105`). `reload.sh` therefore runs `odctl restart mlflow` after the registration (`docs/snippets/mlflow/commands.sh`, section `new-version`). `odctl recreate mlflow` also serves the new version and is not a mistake. `MODEL_URI` needs no change, because it already names the alias (the case's `setup.sh` writes it).
- `odctl restart` runs `docker compose restart` and does not wait for health (`src/odctl/projects.py:41-49`), and the server answers nothing for about 16 seconds while it loads the model (`registry.yml:255`; `docs/guides/mlflow.md:111`). So `score_client.py` retries a refused or failed request, or waits on `http://mlflow-serve:5003/ping` (the service and port of `compose-mlops.yml`; `registry.yml:258` gives the host address), with a limit, and fails with a message when the limit passes. A limit that covers the 16 seconds with a margin, and says so, is right; for example 5 seconds apart for up to a minute.
- The request is `POST http://mlflow-serve:5003/invocations` with a JSON body such as `{"inputs": [...]}` or `{"dataframe_split": ...}`, and the client checks the body for `predictions`, because a scoring failure answers 400 with the error in the body and `curl` without `--fail` still exits 0 (`docs/guides/mlflow.md:97-101`).

## Wrong answers seen or expected

- A2: a client that sends one request after the restart with no retry, or `reload.sh` that calls the server straight after `odctl restart mlflow`, or a reply that says the new version is served once `reload.sh` returns. A `reload.sh` that makes no call to the server, with a client that retries within a limit, is right.
- A3: `http://127.0.0.1:5004`, `localhost:5000` or `http://127.0.0.1:5003` in code that runs in a container; `http://mlflow:5004` or `http://mlflow-serve:5000`.
- A6: no restart or recreate, on the claim that the server follows the alias by itself;
- A4: a claim that `odctl restart mlflow` applies a changed `.env`.
- A12: a retry count, interval or timeout with no reason beside it.
- A2: a wait with no limit.
