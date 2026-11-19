# mlflow-register-serve

Answer sheet of the case `mlflow-register-serve`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A1 (a step needs an earlier step), A3 (address from the wrong side, or guessed), A8 (stack setting assumed).

## Records

- planning `odctl/release/1.4.0/reader-check.md:9`, `:10`: a step run before the step it needs.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): a container address put where the host reads it.
- planning `odctl/release/1.8.0/review-round1.md:20` (M7): a setting said to change one way, when in odctl only an edit of the workspace file and a recreate change it.

## Right answer

- The order is: register the run's model and set the alias, then set `MODEL_URI`, then replace the `mlflow` containers, then score. The model server resolves `MODEL_URI` when its container starts (`docs/guides/mlflow.md:105`), so serving before the version and its alias exist fails: `mlflow-serve`'s health check calls `/ping` once `MODEL_URI` is set (`src/odctl/resources/compose-mlops.yml:182-190`), and the recreate then fails.
- From the laptop the tracking server is `http://127.0.0.1:5004` (`src/odctl/resources/registry.yml:249-251`; `docs/guides/mlflow.md:19`). Host port 5000 is not MLflow: the compose file maps 5004 because macOS binds 5000 to the AirPlay receiver (`compose-mlops.yml:100-101`). `localhost:5004` also works, because `--allowed-hosts` lists it (`compose-mlops.yml:148`).
- `register.py` sets the tracking URI to that address, registers `runs:/<RUN_ID>/model` as `churn-model` (for example `mlflow.register_model`), and points `champion` at the version that call returns (`MlflowClient().set_registered_model_alias`), as the guide's registration does (`docs/guides/mlflow.md:62-77`). Registering needs no S3 address or keys, because the server proxies artifacts (`docs/guides/mlflow.md:52`; `compose-mlops.yml:143-145`). The host client should be MLflow 3.18.0, the server's version (`docs/guides/mlflow.md:24`); a reply that names no client version is not counted wrong for that.
- `MODEL_URI` is a key of `.odctl/.env`, which `odctl init` wrote empty (`src/odctl/workspace.py:151-162`), and compose passes it to `mlflow-serve` (`compose-mlops.yml:172`). `serve.sh` sets it to `models:/churn-model@champion` (`docs/snippets/mlflow/model-uri.env`), then runs `odctl recreate mlflow` (`docs/guides/mlflow.md:93-96`). `odctl up mlflow` also applies it, as the profile's notes say (`registry.yml:252-253`; `compose-mlops.yml:155-156`), so it is not a mistake. `odctl restart mlflow` does not, because a restart keeps the container and its environment (`docs/how-it-works.md:159`).
- `recreate` waits until the services are healthy (`src/odctl/projects.py`, `recreate_managed_containers`, `wait=True`), and that health check is `/ping` once a model is set, so no further wait is needed before scoring. An extra bounded wait on `/ping` is harmless and not counted.
- Scoring from the laptop is `POST http://127.0.0.1:5003/invocations` with a JSON body such as `{"inputs": [[0.5, 1.2], [3.1, 0.4]]}` (`registry.yml:256`; `docs/guides/mlflow.md:97-98`). The script checks the body for `predictions`, because a scoring failure answers 400 with the error in the body and `curl` without `--fail` still exits 0 (`docs/guides/mlflow.md:101`).

## Wrong answers seen or expected

- A1: setting `MODEL_URI` and starting or recreating `mlflow` before the version and its alias exist, or scoring before the server was replaced.
- A3: `http://127.0.0.1:5000` or `http://localhost:5000` as the tracking URI from the laptop, `http://mlflow:5000` or `http://mlflow-serve:5003` from the laptop.
- A6: an S3 endpoint and keys said to be needed for registration.
- A8: `MODEL_URI` set anywhere but `.odctl/.env` with no reason (one exported in the shell applies to that one `odctl recreate`, because a shell variable wins over `.env`, `src/odctl/docker.py:281-299`, and is lost on the next `up` or `recreate`), an edit of the packaged compose file, or `odctl restart mlflow` to apply it.
