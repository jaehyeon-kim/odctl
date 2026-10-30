# Commands from docs/guides/langfuse.md. .github/scripts/smoke.sh runs the run,
# read and tempo sections.

# smoke.sh does not run the up section, because the e2e workflow starts each
# profile itself; it is the command as the page shows it.
# --8<-- [start:up]
odctl up langfuse
# --8<-- [end:up]

# --8<-- [start:run]
uv run --with "opentelemetry-sdk>=1.45,<2" --with "opentelemetry-exporter-otlp-proto-http>=1.45,<2" python send.py
# --8<-- [end:run]

# --8<-- [start:read]
# This prints the name and type of each observation of the trace.
curl -s -u pk-lf-odctl:sk-lf-odctl -G http://127.0.0.1:3005/api/public/v2/observations \
  --data-urlencode "traceId=$TRACE_ID" \
  | python3 -c "import json, sys; [print(o['name'], o['type']) for o in sorted(json.load(sys.stdin)['data'], key=lambda o: o['name'])]"
# --8<-- [end:read]

# --8<-- [start:tempo]
# Set TRACE_ID to the second ID the script printed. Tempo answers 200 when it
# holds the trace and 404 when it does not.
docker exec otel-lgtm curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:3200/api/traces/$TRACE_ID"
# --8<-- [end:tempo]
