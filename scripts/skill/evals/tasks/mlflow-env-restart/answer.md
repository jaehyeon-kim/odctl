# mlflow-env-restart

Answer sheet of the case `mlflow-env-restart`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A7 (what a command keeps or removes), A8 (stack setting assumed), A4 (odctl CLI behaviour assumed).

## Records

- planning `odctl/release/1.2.1/progress.md:41`: a recreate keeps PostgreSQL and SeaweedFS data through their volumes and loses what other containers hold.
- planning `odctl/release/1.8.0/review-round1.md:20` (M7): a setting said to change one way, when in odctl only an edit of the workspace file and a recreate change it.
- planning `odctl/release/1.4.0/review-batch2-round1.md:12` (M3): an extra readiness probe after a command that already waits for the health check.

## Right answer

- `odctl restart mlflow` runs `docker compose restart` (`src/odctl/projects.py:49`), which keeps the container and its environment, so it does not apply an edited `.env` (`docs/how-it-works.md:159`; Docker docs, `docker compose restart`: "changes to environment variables ... are not updated after restarting").
- `odctl recreate mlflow` replaces the containers from the current files, so `mlflow-serve` starts with the new `MODEL_URI` and both containers install `_MLOPS_PIP_DEPS` (`src/odctl/projects.py:52-86`; `docs/guides/mlflow.md:93-96`, 207; `docs/how-it-works.md:226-238`; the keys reach the containers at `src/odctl/resources/compose-mlops.yml:14`, 172). `odctl up mlflow` also replaces a container whose definition changed (the comment at `compose-mlops.yml:155-156` says so; inferred from that comment, not from Compose's source), so it is not a mistake.
- What is kept: MLflow keeps experiments, runs and the model registry in the PostgreSQL database `mlflow` and the artifacts in `s3://mlflow` on SeaweedFS (`compose-mlops.yml:107`, 143-144). `recreate` acts only on the named profile, not on `postgres` or `storage` (`docs/how-it-works.md:49`), and even a recreate of those keeps their volumes (`docs/how-it-works.md:72`). So `odctl recreate mlflow` loses none of them. `odctl down mlflow` and `up mlflow` would keep them too, for the same reason, but `down postgres` or `down storage` would not.
- `recreate` waits as `up` does (`projects.py:81-86`, `wait=True`), and `mlflow-serve`'s health check calls `/ping` once `MODEL_URI` is set (`compose-mlops.yml:185-190`), so the command fails if the model does not load. No extra wait is needed for that.
- Each new container installs the packages from PyPI, so it needs network access (`docs/how-it-works.md:238`).

## Wrong answers seen or expected

- A4: `odctl restart mlflow` again, or a statement that restart applies `.env`.
- A7: `odctl down postgres`, `down storage`, any `down --volumes`, or `down --all`, or a statement that `recreate mlflow` loses the runs or the registered models.
- A8: an edit of the packaged compose file or of `compose-mlops.yml` in place of the `.env` keys the user already set.
- A4: a `curl` loop on `/ping` or `/health` after `recreate`, which already waits for both health checks.
- A4: `odctl recreate mlflow-serve` or `odctl restart mlflow-serve` (a service, not a profile).
