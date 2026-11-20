# Steps from docs/guides/langfuse.md. .github/scripts/smoke.sh runs these sections
# in one process, send first and then telemetry, with the client versions that
# commands.sh:run installs.

# --8<-- [start:send]
import base64
import json

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

ENDPOINT = "http://127.0.0.1:3005/api/public/otel/v1/traces"
AUTH = base64.b64encode(b"pk-lf-odctl:sk-lf-odctl").decode()

provider = TracerProvider(resource=Resource.create({"service.name": "demo"}))
provider.add_span_processor(
    SimpleSpanProcessor(
        OTLPSpanExporter(
            endpoint=ENDPOINT,
            headers={
                "Authorization": f"Basic {AUTH}",
                "x-langfuse-ingestion-version": "4",
            },
        )
    )
)
tracer = provider.get_tracer("demo")


def send_trace(question):
    """Send one trace of a question and its answer, and return its trace ID."""
    with tracer.start_as_current_span("answer-question") as root:
        root.set_attribute("langfuse.observation.input", json.dumps(question))
        with tracer.start_as_current_span("model-call") as call:
            call.set_attribute("gen_ai.request.model", "stand-in-model")
            call.set_attribute("langfuse.observation.input", json.dumps(question))
            # odctl runs no model, so a fixed answer stands in for the model call.
            answer = "Langfuse stores traces."
            call.set_attribute("langfuse.observation.output", json.dumps(answer))
        root.set_attribute("langfuse.observation.output", json.dumps(answer))
        return format(root.get_span_context().trace_id, "032x")


print(send_trace("What does Langfuse store?"))
# --8<-- [end:send]

# --8<-- [start:telemetry]
# The collector from `odctl up telemetry` receives OTLP over HTTP on port 4318.
provider.add_span_processor(
    SimpleSpanProcessor(OTLPSpanExporter(endpoint="http://127.0.0.1:4318/v1/traces"))
)
print(send_trace("Does this trace reach Tempo too?"))
# --8<-- [end:telemetry]
