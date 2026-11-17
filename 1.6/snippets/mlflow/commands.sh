# Commands from docs/guides/mlflow.md. .github/scripts/smoke.sh runs each
# section after it puts model-uri.env or model-uri-features.env into .odctl/.env.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up mlflow
# --8<-- [end:up]

# --8<-- [start:serve]
odctl recreate mlflow
curl -X POST http://127.0.0.1:5003/invocations \
  -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}'
# --8<-- [end:serve]

# --8<-- [start:new-version]
odctl restart mlflow
# The server answers nothing while the model loads: 16 seconds in one run.
until curl -fs http://127.0.0.1:5003/ping >/dev/null; do sleep 2; done
curl -X POST http://127.0.0.1:5003/invocations \
  -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}'
# --8<-- [end:new-version]

# --8<-- [start:features-score]
curl -X POST http://127.0.0.1:5003/invocations \
  -H 'Content-Type: application/json' \
  -d '{"dataframe_split": {"columns": ["driver_id"], "data": [[1001]]}}'
# --8<-- [end:features-score]
