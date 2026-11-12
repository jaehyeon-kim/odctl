#!/usr/bin/env bash
# Starts lineage, reports one run of a job that reads raw-orders and writes
# demo-dataset, and prints the state of the job's latest run.
set -euo pipefail

odctl up lineage

RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
for event in START COMPLETE; do
  curl -s -X POST http://127.0.0.1:5002/api/v1/lineage \
    -H 'Content-Type: application/json' \
    -d "{\"eventType\":\"$event\",\"eventTime\":\"$NOW\",
         \"producer\":\"demo\",
         \"run\":{\"runId\":\"$RUN_ID\"},
         \"job\":{\"namespace\":\"demo\",\"name\":\"demo-job\"},
         \"inputs\":[{\"namespace\":\"demo\",\"name\":\"raw-orders\"}],
         \"outputs\":[{\"namespace\":\"demo\",\"name\":\"demo-dataset\"}]}"
done

curl -s http://127.0.0.1:5002/api/v1/namespaces/demo/jobs/demo-job \
  | python3 -c 'import json, sys; run = json.load(sys.stdin)["latestRun"]; print(run["id"], run["state"])'
