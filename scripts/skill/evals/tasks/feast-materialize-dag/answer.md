# feast-materialize-dag

Answer sheet of the case `feast-materialize-dag`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A6 (service behaviour stated without a run or its source), A3 (address from the wrong side, or guessed), A2 (service called before it is ready).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:7` (S3): `materialize_incremental` said to copy "the values written since the previous run"; it copies rows by their event timestamp.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): a host address put into a repository that a container reads.
- planning `odctl/release/1.4.0/review-batch1-round3.md:5` (S1): `airflow dags unpause` exits 0 before the DAG is parsed, and the DAG stays paused.

## Right answer

- The DAG runs in the `airflow` container, which has the Feast client with the needed extras (`src/odctl/resources/docker/airflow/Dockerfile:30-33`), so it installs nothing. It cannot read `feature_repo/` on the laptop, and that folder's `feature_store.yaml` holds host addresses (`127.0.0.1:5432`, `127.0.0.1:6379`, written by the case's `setup.sh`). The DAG builds the store in code with `RepoConfig`: project `demo`, the SQL registry from `FEAST_REGISTRY`, which the container sets to `postgres:5432/feast` (`src/odctl/resources/compose-orch.yml:45-46`), the DuckDB offline store, and the Valkey online store at `valkey:6379,username=user,password=password` (`docs/snippets/feast-iceberg/feast_materialize.py`; `docs/guides/feast-iceberg.md:121-125`). The Iceberg source names no address; PyIceberg takes `http://catalog:8181` from the container's `PYICEBERG_CATALOG__ODCTL__*` variables (`compose-orch.yml:55-62`; `docs/guides/feast-iceberg.md:102`). Uploading a copy of the repository into the container with container addresses is also right.
- Every hour: `schedule="@hourly"` with `catchup=False`, and a task that calls `store.materialize_incremental(end_date=<now in UTC>)` (`docs/guides/feast-iceberg.md:129-171`). It copies the rows whose `event_timestamp` falls between the end of the previous materialisation and `end_date`, so a row written later with an older timestamp is not copied (`docs/guides/feast-iceberg.md:119`). A reply that says it copies every row written since the last run, or the whole table each time, states the behaviour wrongly.
- The check task calls the feature server from the container: `POST http://feast-serve:6566/get-online-features` with `{"features": ["driver_stats:conv_rate"], "entities": {"driver_id": [1001]}}` (`docs/guides/feast-iceberg.md:291-295`, 391; `src/odctl/resources/registry.yml:270-272`), and fails the task when the value is missing or null. Reading with the SDK's `get_online_features` in the task does not check the feature server, as the request asks.
- `deploy.sh` uploads the DAG to `s3://airflow/dags`, for example by `docker cp` and boto3 in the `airflow` container with `http://seaweed:8333` (`docs/guides/feast-iceberg.md:177-185`), or from the host at `http://127.0.0.1:8333` with `user` and `password` (`docs/guides/airflow-dags.md:23`). Airflow reads the bucket every 15 seconds (`registry.yml:219`), so the script waits, with a limit, until `airflow dags list` shows the DAG before it unpauses: before that, `unpause` prints `No paused DAGs were found`, exits 0 and changes nothing, and `trigger` fails (`docs/guides/feast-iceberg.md:202`). New DAGs start paused (`compose-orch.yml:29`), so the script unpauses, triggers, and waits with a limit until the run is `success` or `failed`.
- Unpausing also starts one scheduled run for the latest hour that has ended (`docs/guides/feast-iceberg.md:202`); a reply need not mention it.

## Wrong answers seen or expected

- A6: a statement that `materialize_incremental` copies every new row, or that `materialize` and `materialize_incremental` are the same, with no source.
- A3: `127.0.0.1` or `localhost` for the registry, Valkey or the feature server inside the DAG; `FeatureStore(repo_path="feature_repo")` in the DAG; `http://feast-serve:8888` or `http://feast-ui:6566`.
- A2: unpause or trigger straight after the upload with no wait for the DAG to be parsed, a fixed `sleep` in its place, or a wait with no limit.
