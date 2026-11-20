# airflow-trigger-api

Answer sheet of the case `airflow-trigger-api`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository. Paths that start with `airflow-core/` are in Apache Airflow at tag `3.3.2`, the base of odctl's Airflow image (`src/odctl/resources/docker/airflow/Dockerfile:1`).

Kinds: A2 (service called before it is ready), A3 (address from the wrong side, or guessed), A8 (stack setting assumed), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.4.0/review-batch1-round3.md:5` (S1): `airflow dags unpause` exits 0 before the DAG is parsed, and the DAG stays paused.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit.
- A12 has no odctl record; this case extends the evidence of desflow's K14 that `plan-agent-skill.md`, Kinds of mistake, row A12, cites.

## Right answer

- From the laptop Airflow's API is `http://127.0.0.1:8085`, with user `user` and password `password` (`src/odctl/resources/registry.yml:216-217`; `src/odctl/resources/compose-orch.yml:93`; `docs/guides/airflow-dags.md:17`). Host port 8080 is Trino (`registry.yml:191`), and `http://airflow:8080` resolves only inside the network.
- odctl's Airflow uses the simple auth manager (`compose-orch.yml:25-27`). The script gets a token with `POST http://127.0.0.1:8085/auth/token` and the JSON body `{"username": "user", "password": "password"}`, which answers 201 with `access_token` (`airflow-core/src/airflow/api_fastapi/auth/managers/simple/routes/login.py:37-69`; mounted at `/auth` by `airflow-core/src/airflow/api_fastapi/app.py:209`), and sends it as `Authorization: Bearer <token>`. Basic auth on `/api/v2` is not the answer.
- The DAG was uploaded seconds ago. Airflow reads the bucket every 15 seconds (`registry.yml:219`; `compose-orch.yml:65-69`) and then parses the file, and until then `POST /api/v2/dags/daily_sales/dagRuns` answers 404 (`airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:752-763`). The script waits for the DAG, for example `GET /api/v2/dags/daily_sales` until it answers 200, with a limit and the reason beside it.
- New DAGs start paused in odctl (`AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: "true"`, `compose-orch.yml:29`), and the scheduler starts a queued run only for a DAG that is not paused (`airflow-core/src/airflow/models/dagrun.py:720-726`), so a run triggered on a paused DAG stays `queued`. The script unpauses it with `PATCH /api/v2/dags/daily_sales` and `{"is_paused": false}` (`routes/public/dags.py:265-291`).
- It triggers with `POST /api/v2/dags/daily_sales/dagRuns` and a body that holds `logical_date`, which the model requires though it may be null (`airflow-core/src/airflow/api_fastapi/core_api/datamodels/dag_run.py:225-231`), and takes `dag_run_id` from the answer.
- It polls `GET /api/v2/dags/daily_sales/dagRuns/<dag_run_id>` (`routes/public/dag_run.py:129-130`) until `state` is `success` or `failed`, with a limit whose reason it gives, and exits 1 on `failed` or when the limit passes.

## Wrong answers seen or expected

- A2: trigger or unpause straight after the upload with no wait for the DAG to be parsed, or a fixed `sleep` in its place.
- A3: `http://127.0.0.1:8080` or `http://localhost:8080` (Trino on the host), `http://airflow:8080` from the laptop, or `admin`/`admin`.
- A6: guessed Airflow 2 paths such as `/api/v1/dags/...` with Basic auth.
- A8: no unpause, on the assumption that a new DAG runs when triggered.
- A12: a poll interval, retry count or overall limit with no reason beside it.
- A2: a wait with no limit.
