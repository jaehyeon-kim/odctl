#!/usr/bin/env bash
# Starts telemetry, sends one OTLP metric to the collector and waits until
# Prometheus returns it.
set -euo pipefail

odctl up telemetry

ts=$(python3 -c "import time;print(int(time.time()*1e9))")
curl -s -X POST -H "Content-Type: application/json" http://127.0.0.1:4318/v1/metrics -d @- <<JSON
{"resourceMetrics":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"demo"}}]},
"scopeMetrics":[{"scope":{"name":"demo"},"metrics":[{"name":"demo_total","unit":"1",
"sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[
{"asDouble":42,"timeUnixNano":"${ts}","startTimeUnixNano":"${ts}","attributes":[]}]}}]}]}]}
JSON
echo

# The collector passes metrics on in batches, so the first queries can be empty.
until curl -s "http://127.0.0.1:19090/api/v1/query?query=demo_total" | grep '"42"' >/dev/null; do
  sleep 2
done
curl -s "http://127.0.0.1:19090/api/v1/query?query=demo_total"
echo
