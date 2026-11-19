# marquez-run-report

Answer sheet of the case `marquez-run-report`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository. Paths that start with `api/` are in Marquez at tag `0.51.1`, the image's version (`src/odctl/resources/compose-obsv.yml:8`).

Kinds: A3 (address from the wrong side, or guessed), A9 (state from an earlier run breaks the next), A6 (service behaviour stated without a run or its source).

## Records

- planning `odctl/release/1.8.0/review-round1.md:8` (S2): the guide said Marquez names the jobs; the sender names them.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.
- planning `odctl/release/1.4.0/audit.md:10` (S2): a second run on one stack passed or failed on what the first run left.

## Right answer

- From the laptop the Marquez API is `http://127.0.0.1:5002`; `5000` is its port inside the network (`http://marquez-api:5000`) and `5001` is the admin port (`src/odctl/resources/compose-obsv.yml:15-16`; `src/odctl/resources/registry.yml:307-309`; `docs/guides/lineage.md:23-24`). Events go to `POST http://127.0.0.1:5002/api/v1/lineage` (`docs/guides/lineage.md:31-45`).
- Each run is a `START` event and an end event with the same `run.runId`, which is a UUID (`docs/guides/lineage.md:29`, 47). Each run of the job needs a new UUID: the start call makes one and the end call uses the same one, so the start call keeps it somewhere the end call reads, such as a file or the job's environment. A fixed id, as the guide's first example uses (`docs/guides/lineage.md:32`), makes every night's report the same run; the guide's runnable example makes a new one each time (`docs/guides/lineage.md:309`, 319).
- The end event is `COMPLETE` on success and `FAIL` on failure. Marquez stores them as the run states `COMPLETED` and `FAILED`, and `START` as `RUNNING` (`api/src/main/java/marquez/db/OpenLineageDao.java:1103-1117`).
- The sender names the job and the datasets: `job` with a namespace of the script's choosing and the name `nightly_orders`, `inputs` with `raw.orders` and `outputs` with `mart.daily_orders`, each with a namespace, and `eventTime` and `producer` set (`docs/guides/lineage.md:35-44`).
- `latest_run.sh` reads `GET http://127.0.0.1:5002/api/v1/namespaces/<namespace>/jobs/nightly_orders` and prints `latestRun.state` (`docs/guides/lineage.md:53-59`, 332-333).

## Wrong answers seen or expected

- A3: `http://127.0.0.1:5000`, `http://localhost:5000`, `:5001` or `http://marquez-api:5000` from the laptop.
- A9: one fixed `runId` for every run.
- A1: a new id made at the end call, so that the start and end events belong to different runs.
- A6: `FAILED` or `ERROR` sent as the event type; a claim that Marquez names the job or the run. A non-UUID run id unique to the run is right: Marquez 0.51.1 turns it into a name-based UUID (`OpenLineageDao.java:1143-1150`, `runToUuid`).
