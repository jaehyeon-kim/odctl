# Commands from docs/guides/mlflow.md. .github/scripts/smoke.sh runs this
# section after it puts model-uri.env into .odctl/.env.

# --8<-- [start:serve]
odctl up mlflow
curl -X POST http://127.0.0.1:5003/invocations \
  -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}'
# --8<-- [end:serve]
