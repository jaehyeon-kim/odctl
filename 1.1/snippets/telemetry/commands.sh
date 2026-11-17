# Commands from docs/guides/telemetry.md. .github/scripts/smoke.sh runs this section.

# --8<-- [start:send-metric]
ts=$(python3 -c "import time;print(int(time.time()*1e9))")
cat > /tmp/otlp.json <<JSON
{"resourceMetrics":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"demo"}}]},
"scopeMetrics":[{"scope":{"name":"demo"},"metrics":[{"name":"demo_total","unit":"1",
"sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[
{"asDouble":42,"timeUnixNano":"${ts}","startTimeUnixNano":"${ts}","attributes":[]}]}}]}]}]}
JSON
curl -X POST -H "Content-Type: application/json" --data-binary @/tmp/otlp.json \
  http://127.0.0.1:4318/v1/metrics
curl "http://127.0.0.1:19090/api/v1/query?query=demo_total"
# --8<-- [end:send-metric]
