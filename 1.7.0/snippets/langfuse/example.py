"""Sends one trace to Langfuse and waits until its two observations can be read back.

Start the profile with `odctl up langfuse` first, then run this file with
`uv run --with "opentelemetry-sdk>=1.45,<2" --with "opentelemetry-exporter-otlp-proto-http>=1.45,<2" python example.py`.
"""

import base64
import json
import time
import urllib.parse
import urllib.request

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

BASE = "http://127.0.0.1:3005/api/public"
AUTH = base64.b64encode(b"pk-lf-odctl:sk-lf-odctl").decode()

provider = TracerProvider()
provider.add_span_processor(
    SimpleSpanProcessor(
        OTLPSpanExporter(
            endpoint=f"{BASE}/otel/v1/traces",
            headers={
                "Authorization": f"Basic {AUTH}",
                "x-langfuse-ingestion-version": "4",
            },
        )
    )
)
tracer = provider.get_tracer("demo")

with tracer.start_as_current_span("answer-question") as root:
    with tracer.start_as_current_span("model-call") as call:
        # odctl runs no model, so this span only carries a model name.
        call.set_attribute("gen_ai.request.model", "stand-in-model")
    trace_id = format(root.get_span_context().trace_id, "032x")

query = urllib.parse.urlencode({"traceId": trace_id})
request = urllib.request.Request(
    f"{BASE}/v2/observations?{query}", headers={"Authorization": f"Basic {AUTH}"}
)
# Langfuse writes the trace to ClickHouse a moment after it receives it.
for _ in range(30):
    with urllib.request.urlopen(request) as response:
        observations = json.load(response)["data"]
    if len(observations) == 2:
        break
    time.sleep(2)
print(f"trace {trace_id} has {len(observations)} observations")
