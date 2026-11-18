# om-ingest-postgres

Answer sheet of the case `om-ingest-postgres`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository. Paths that start with `openmetadata-service/` are in OpenMetadata at tag `2.0.8-release`, the server image's version (`src/odctl/resources/compose-metadata.yml:36`).

The script calls the API from the host, and the address it gives OpenMetadata for PostgreSQL is used from a container, so the case covers the `metadata` profile from both sides.

Kinds: A3 (address from the wrong side, or guessed), A9 (state from an earlier run breaks the next), A2 (service called before it is ready), A12 (a number given with no reason).

## Records

- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.
- planning `odctl/release/1.4.0/audit.md:10` (S2): a second run on one stack passed or failed on what the first run left.
- planning `architecting-analytics/validation-live-stack.md:55`: a create step that was not safe to run twice.
- planning `odctl/release/1.4.0/review-batch1-round3.md:5` (S1): a call made before Airflow had parsed the DAG.
- A12 has no odctl record; this case extends the evidence of desflow's K14 that `plan-agent-skill.md`, Kinds of mistake, row A12, cites.

## Right answer

- From the laptop the API is `http://127.0.0.1:8585` (`src/odctl/resources/registry.yml:337-342`; `docs/guides/openmetadata.md:15`). The token comes from `POST /api/v1/users/login` with `admin@odctl.io` and the password `password` base64-encoded, and later calls send `Authorization: Bearer <accessToken>` (`docs/guides/openmetadata.md:19-31`).
- The service's `hostPort` is `postgres:5432`, with user `user`, password `password` and database `odctl` (`docs/guides/openmetadata.md:37-43`; `registry.yml:25-28`). The server tests the connection and the ingestion runs in the `openmetadata-ingestion` container (`docs/guides/openmetadata.md:3`; `compose-metadata.yml:115`, 135-137), where `127.0.0.1:5432` is that container itself.
- Safe to run twice: the service is created with `PUT /api/v1/services/databaseServices`, which creates or updates (`docs/guides/openmetadata.md:39-43`). The agent too: a second `POST /api/v1/services/ingestionPipelines` with the same name fails with 409, because the name already exists (`openmetadata-service/src/main/java/org/openmetadata/service/exception/CatalogGenericExceptionMapper.java:57-61`), so the script uses `PUT` on the same path, which creates or updates (`openmetadata-service/.../resources/services/ingestionpipelines/IngestionPipelineResource.java:713-740`), or reads the agent by name and creates it only when it is missing.
- It deploys the agent (`POST .../ingestionPipelines/deploy/<id>`), then triggers it (`POST .../trigger/<id>`), repeating the trigger every few seconds, with a limit, until it answers that the workflow has been triggered, because the ingestion Airflow has to parse the new DAG first (`docs/guides/openmetadata.md:62-72`; `.github/scripts/smoke.sh:1553-1562`, 24 tries 5 seconds apart).
- It waits, with a limit, until `pipelineStatuses` of `.../ingestionPipelines/name/<service>.<agent>?fields=pipelineStatuses` ends in `success`, `failed` or `partialSuccess`, and exits non-zero unless it is `success` (`docs/guides/openmetadata.md:74-79`). On the second run the first entry is still the earlier run, already `success`, so the script waits for a run whose id differs from the one it saw before the trigger (`smoke.sh:1576-1589`). A script that takes the first entry's state at once passes on every run after the first without waiting.
- Each limit has its reason beside it, such as the time the ingestion takes on a laptop.

## Wrong answers seen or expected

- A3: `hostPort` `127.0.0.1:5432` or `localhost:5432`; `http://openmetadata-server:8585` from the laptop; `admin`/`admin` or `admin@open-metadata.org`.
- A9: `POST` for the agent with no check for an existing one, so the second build gets 409; a state read that accepts the earlier run's `success`.
- A2: one trigger straight after the deploy with no retry, or a fixed `sleep` in place of a retry.
- A12: a retry count, interval or overall limit with no reason beside it.
- A2: a wait with no limit.
