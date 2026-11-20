# langfuse-trace

Answer sheet of the case `langfuse-trace`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A2 (service called before it is ready), A6 (service behaviour stated without a run or its source).

## Records

- planning `odctl/release/1.7.0/review-round1.md:7`: healthy Langfuse containers taken to mean a trace is stored.
- planning `odctl/release/1.7.0/review-round1.md:8`: the read said to need a time range; it does not.
- planning `odctl/release/1.7.0/reader-check.md:5`, `:7`: an address given with no command that shows it answers.

## Right answer

- `odctl up langfuse`, which starts `postgres`, `storage`, `ch-lite` and `valkey`, and cannot run beside `ch-full` (`registry.yml:357`, 369).
- From a container on the `odctl` network: `http://langfuse-web:3000/api/public/otel/v1/traces`; from the host: `http://127.0.0.1:3005` (`compose-aieng.yml:56`).
- Auth: HTTP Basic `pk-lf-odctl:sk-lf-odctl` and the header `x-langfuse-ingestion-version: 4` (`registry.yml:366-368`).
- A container on the network: `docker run --rm --network odctl curlimages/curl:8.17.0 ...` (`docs/snippets/langfuse/commands.sh` `container`, lines 27 to 34).
- Stored: `GET /api/public/v2/observations?traceId=<id>` with the keys, repeated with a limit, because the worker writes to ClickHouse after the send (`snippet read`, lines 14 to 19; `smoke.sh:2163-2187`). `/api/public/traces` answers 404 in Langfuse 4 (`docs/guides/langfuse.md:106`).

## Wrong answers seen or expected

- `localhost:3005` or `langfuse-web:3005` from a container; port 3000 from the host.
- A healthy container or a 200 on the send taken as the trace being stored.
- Reading `/api/public/traces`, or saying a time range is required.
- No ingestion header.
