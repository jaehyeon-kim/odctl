# airflow-openlineage

Answer sheet of the case `airflow-openlineage`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

The setting is read by Airflow inside the network and the check runs on the laptop, so the case covers the `lineage` and `airflow` profiles from both sides.

Kinds: A8 (stack setting assumed), A3 (address from the wrong side, or guessed), A6 (service behaviour stated without a run or its source).

## Records

- planning `odctl/release/1.8.0/review-round1.md:20` (M7): Airflow's lineage namespace said to change one way, when in odctl only an edit of the workspace file and a recreate change it.
- planning `odctl/release/1.8.0/review-round1.md:8` (S2): the guide said Marquez names the jobs; the sender names them.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.

## Right answer

- The setting is the `.env` key `AIRFLOW_OPENLINEAGE_TRANSPORT`, which `odctl init` writes empty with a commented example (`src/odctl/workspace.py:116-127`), and which compose passes to Airflow as `AIRFLOW__OPENLINEAGE__TRANSPORT` (`src/odctl/resources/compose-orch.yml:15-18`). Empty, the provider sends nothing (`docs/guides/lineage.md:67`).
- Its value is `{"type": "http", "url": "http://marquez-api:5000"}`: Airflow sends from inside the `odctl` network, so the URL is Marquez's container address, and the HTTP transport adds `api/v1/lineage` itself (`docs/guides/lineage.md:69-73`, 305). `enable_lineage.sh` sets it in `.odctl/.env`, for example with the guide's `sed` (`docs/snippets/lineage/commands.sh`, section `airflow-env`).
- It starts Marquez with `odctl up lineage` (`docs/guides/lineage.md:17-19`), then runs `odctl recreate airflow`: Airflow is already running, and a restart keeps the container, so it does not read `.env` again (`docs/guides/lineage.md:79`; `docs/how-it-works.md:159`). The recreate keeps the run history, which is in the `airflow` database on PostgreSQL (`compose-orch.yml:22`), and PostgreSQL is neither recreated nor its data lost (`docs/how-it-works.md:49`, 72). The DAGs stay in `s3://airflow/dags` (`registry.yml:219`).
- `check_lineage.sh` reads `GET http://127.0.0.1:5002/api/v1/namespaces/default/jobs/daily_sales` (the jobs endpoint of `docs/guides/lineage.md:143-150`; the listing returns at most 100 jobs by default, Marquez 0.51.1 `JobResource.java:180-186`, so with several DAGs a listing can miss it). Airflow puts its jobs in the namespace `default`, names the DAG's job `daily_sales` and each task's job `daily_sales.<task_id>` (`docs/guides/lineage.md:153-161`). The check exits 0 when a job of that name, or one that starts with `daily_sales.`, is listed, and 1 otherwise. A check that retries with a limit is also right.

## Wrong answers seen or expected

- A8: `odctl restart airflow` after the edit, or an edit of the packaged compose file or of `compose-orch.yml` in place of the `.env` key; `odctl down airflow` with the claim that it is needed.
- A3: `http://127.0.0.1:5002` or `localhost:5002` in the transport URL; `http://marquez-api:5000/api/v1/lineage` as the transport URL, though the transport adds that path itself (`docs/guides/lineage.md:305`); `marquez-api:5000` or `127.0.0.1:5000` in the laptop's check.
- A6: a namespace other than `default`, or job names other than the DAG and `<dag>.<task>`, stated with no source; a claim that Marquez names the jobs.
