# promql-token-budget

Answer sheet of the case `promql-token-budget`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A6 (service behaviour stated without a run or its source), A3 (address from the wrong side, or guessed).

## Records

- planning `odctl/release/1.8.0/review-batch2-round1.md:9` (S3): `increase()` ignores a new series' first sample, so a script that exports once is never counted.
- planning `odctl/release/1.8.0/review-batch2-round2.md:7`: the same fault came back, because the query was reasoned about from `increase()` alone.
- planning `odctl/release/1.4.0/review-batch1-round2.md:5` (S1): an address from the other side of the network used.

## Right answer

- Inside the `odctl` network Prometheus is `http://prometheus:9090` or `http://otel-lgtm:9090`: the `otel-lgtm` container has the network alias `prometheus` (`src/odctl/resources/compose-obsv.yml:69-78`; `src/odctl/resources/registry.yml:314-316`; `docs/guides/telemetry.md:296`). `127.0.0.1:19090` is the host's port and does not reach Prometheus from a container. `run.sh` runs the script with `docker run --rm --network odctl` and an image with Python, as the guide's container commands do (`docs/guides/telemetry.md:300-304`; `docs/how-it-works.md:57-61`).
- The metric's name in Prometheus is `gen_ai_client_token_usage_sum`: Prometheus writes `.` as `_`, and keeps the sum of an explicit-bucket histogram, the SDKs' default, in the series ending in `_sum` (`docs/guides/telemetry.md:206`). This name is documented in the guide and not checked by odctl's tests; `smoke.sh` checks only that the sample rule loads (`.github/scripts/smoke.sh:1256-1263`).
- `increase()` counts only the change after a series' first sample, so `sum(increase(gen_ai_client_token_usage_sum[1h]))` alone misses the tokens of a series' first export and every token of an application that exported once (`docs/guides/telemetry.md:208-213`). The total that the request asks for is the guide's query, `sum((last_over_time(gen_ai_client_token_usage_sum[1h]) unless gen_ai_client_token_usage_sum offset 1h) or increase(gen_ai_client_token_usage_sum[1h]))`, sent as an instant query to `/api/v1/query` (`docs/snippets/telemetry/token_budget.yaml:34`). Another query is right only when it counts a series that began within the hour by its last value.
- An empty result means no model calls in the hour, so the script prints 0 for it, not an error (`token_budget.yaml:53-54` treats no data as under budget).

## Wrong answers seen or expected

- A6: `sum(increase(...[1h]))` or `rate()` times 3600 alone, stated to count every token; the metric name `gen_ai_client_token_usage_total` or `gen_ai_client_token_usage` with no source.
- A3: `http://127.0.0.1:19090`, `localhost:9090` or `host.docker.internal:19090` in the container; `http://grafana:3000` queried as if it were Prometheus.
