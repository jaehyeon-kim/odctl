# fluss-host-gateway

Answer sheet of the case `fluss-host-gateway`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A3 (address from the wrong side), A1 (a step needs an earlier step), A6 (service behaviour stated without a run or its source), A2 (service called before it is ready).

## Records

- github `jaehyeon-kim/odctl#20`: a host client given a Kafka address that the broker advertised for another network (A3); Fluss advertises container names in the same way.
- planning `odctl/release/1.4.0/reader-check.md:9`: a client run before the step it needed (A1).
- planning `odctl/release/1.7.0/review-round1.md:8` (B-S1) and `odctl/release/1.4.0/review-batch1-round2.md:7` (S3): an API's behaviour described from memory (A6).
- planning `odctl/release/1.8.0/reader-check.md:16` (fix 4): a service that answered errors for a while after start (A2).

## Right answer

- `odctl up fluss flink-lite` (`docs/snippets/fluss/commands.sh:7`); `flink-lite` brings `catalog`, `postgres` and `storage` (`--dry-run`).
- No Fluss client on the host: both servers advertise their container names, which resolve only inside the `odctl` network (`registry.yml:160-162`; `docs/guides/fluss.md:16`), and the tablet server advertises `fluss-tablet-1:9123` while it is published on `127.0.0.1:9124` (`compose-store.yml:68-69`, `83`). A host client given `127.0.0.1:9123` reaches the coordinator and is then sent to `fluss-tablet-1:9123`, which the host cannot resolve (inferred from the advertised listeners, not run).
- The way over HTTP is Flink's SQL Gateway, `http://127.0.0.1:8084` from the host (`registry.yml:107`; `compose-flink.yml:85-100`; `docs/guides/flink-sql.md:22`). The statements run inside the network, so the catalog names `'bootstrap.servers' = 'fluss-coordinator:9123'` (`docs/snippets/fluss/steps.sql:8`).
- Gateway calls: `POST /v1/sessions` gives `sessionHandle`; `POST /v1/sessions/<handle>/statements` with `{"statement": "..."}` gives `operationHandle`; `GET /v1/sessions/<handle>/operations/<op>/result/<token>` gives the rows, and `nextResultUri` the next page until it is null (Flink 2.2 docs, `docs/dev/table/sql-gateway/overview/`). A fetch can answer `resultType` `NOT_READY`, so the script fetches again until `PAYLOAD` or `EOS` (apache/flink `release-2.2.0`, `flink-table/flink-sql-gateway-api/.../results/ResultSet.java:87-96`). Under `/v1` the fetch takes no `rowFormat`; under `/v2` to `/v4`, and with no version in the path, it needs `?rowFormat=JSON` (`FetchResultsMessageParameters.java:77-81`; `flink-table/flink-sql-gateway/.../header/statement/FetchResultsHeaders.java:85-92`). Not confirmed by a run: no smoke check calls the gateway.
- One session for every statement: each session builds its own catalog manager (apache/flink `release-2.2.0`, `flink-table/flink-sql-gateway/.../context/SessionContext.java:297-350`), so a catalog created in one session is unknown in the next.
- `SET 'execution.runtime-mode' = 'batch'` and `SET 'table.dml-sync' = 'true'` first (`docs/snippets/fluss/steps.sql:5-6`), so the `INSERT` has finished before the `SELECT`, and the `SELECT` ends. Fluss 1.0 reads a primary-key table in batch mode (fluss.apache.org, Flink Reads, version 1.0).
- `CREATE DATABASE IF NOT EXISTS` and the table with `PRIMARY KEY (id) NOT ENFORCED` (`steps.sql:9-10`); `CREATE TABLE IF NOT EXISTS` lets the script run twice, which the request does not ask for.
- Readiness: the SQL Gateway has no health check (`compose-flink.yml:85-100`), so `odctl up` can return before it answers; the script waits until a gateway call answers (for example `GET /v1/info`, `GetInfoHeaders.java:34`), with a limit. The tablet server registers in ZooKeeper some seconds after it starts (`docs/guides/fluss.md:20`, `83-86`; `smoke.sh:1398-1403`), so `run.sh` waits for that, as the guide's example does, or the script retries the `CREATE TABLE` with a limit.

## Wrong answers seen or expected

- A3: a Fluss client on the laptop with `127.0.0.1:9123`; `127.0.0.1:9123` or `localhost:9123` inside a statement; `http://flink-sql-gateway:8083` or `http://jobmanager:8081` from the laptop; the gateway at `127.0.0.1:8083`, which is Kafka Connect when Kafka runs (`compose-kafka.yml:137-138`).
- A1: a new session for each statement, so the `CREATE TABLE` or `INSERT` names a catalog the session does not have.
- A6: a script that reads the result once after submitting, or states that a statement's result is ready when the submit returns; a streaming `SELECT` expected to end.
- A2: calling the gateway or creating the table straight after `odctl up` with no wait, or a wait with no limit.
