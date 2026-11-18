# grafana-alert-file

Answer sheet of the case `grafana-alert-file`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

The request asks for the alert to survive `odctl down telemetry` and `odctl up telemetry` as well as a restart. A rule made in the UI or through Grafana's API survives a restart, because the container stays, so with the restart alone the task would have two right answers.

Kinds: A7 (what a command keeps or removes), A2 (service called before it is ready), A12 (a number given with no reason), A10 (a check that cannot fail).

## Records

- planning `odctl/release/1.8.0/review-batch2-round1.md:11` (S5): a Grafana contact point made in the UI is lost at `odctl down`, because Grafana's database has no volume.
- planning `odctl/release/1.8.0/reader-check.md:16`: after `odctl restart telemetry` the first request got "Service Unavailable".
- planning `odctl/release/1.7.0/reader-check.md:7`: Grafana's data source proxy failed for about 10 seconds after the stack started.
- planning `odctl/release/1.2.0/review-batch1.md:11`: a check that could not fail.
- A12 has no odctl record; this case extends the evidence of desflow's K14 that `plan-agent-skill.md`, Kinds of mistake, row A12, cites.

## Right answer

- Grafana's database lives in the `otel-lgtm` container with no volume, so a rule made in the UI or through the API is lost at `odctl down telemetry` (`docs/guides/telemetry.md:180`; `src/odctl/resources/compose-obsv.yml:96-105`). Grafana loads alert rules from `.odctl/grafana/alerting/`, mounted at its provisioning folder, each time it starts (`compose-obsv.yml:103-105`; `src/odctl/resources/registry.yml:322-324`; `docs/how-it-works.md:151`). `add_alert.sh` writes a rule file there and runs `odctl restart telemetry`, which loads it (`docs/guides/telemetry.md:56`, 280-283; `docs/how-it-works.md:165`). The file is in the workspace, so it is loaded again after `down` and `up`.
- The file follows the shipped `airflow.yaml`: `apiVersion: 1`, a group with `orgId`, `folder` and `interval`, and a rule with its own `uid` and `title`, a Prometheus query on the data source with uid `prometheus`, a reduce and a threshold (`src/odctl/resources/grafana/alerting/airflow.yaml:7-66`; `docs/guides/telemetry.md:217-278`). The MLflow tracking server is the scrape job `mlflow` (`src/odctl/resources/prometheus/prometheus.yml:90-93`), so the query is `up{job="mlflow"}`, which is 0 while the target cannot be scraped (`docs/guides/telemetry.md:23`). The threshold fires below 1, and `for: 2m` holds it for the 2 minutes the request asks. A query `up{job="mlflow"} == 0` also works when the condition fires on its result, such as a threshold that fires on any value with `noDataState: OK`.
- `check_alert.sh` lists the loaded rules from the laptop, `GET http://127.0.0.1:3004/api/v1/provisioning/alert-rules` with `user` and `password` (`docs/guides/telemetry.md:58-65`; `registry.yml:317-319`), and exits 0 only when the rule's title or uid is in the list. Grafana takes a few seconds to answer after the restart (`docs/guides/telemetry.md:285`), so the check retries with a limit and its reason; odctl's own test retries 12 times, 5 seconds apart (`.github/scripts/smoke.sh:1260-1262`).

## Wrong answers seen or expected

- A7: a rule created through `POST /api/v1/provisioning/alert-rules` or the UI, said to survive `down`; or a file written to the packaged resources or to a path that is not mounted.
- A2: a check straight after `odctl restart telemetry` with no retry, or a fixed `sleep` in place of a retry.
- A12: a retry count, interval or overall limit with no reason beside it.
- A2: a wait with no limit.
- A10: `up{job="mlflow"} == 0` with a threshold `gt 0`, which never fires, because the value while the target is down is 0; or a check that exits 0 on any answer from the API, such as `curl -f` alone.
