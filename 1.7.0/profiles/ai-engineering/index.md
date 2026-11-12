# AI Engineering

## Langfuse

Profiles: `langfuse`. Stack `aieng`, defined in `compose-aieng.yml`.

### langfuse

Depends on: `postgres`, `storage`, `ch-lite`, `valkey`. `odctl up langfuse` also starts: `ch-lite`, `deps`, `postgres`, `storage`, `valkey`.

```text
• Langfuse UI (Credentials: user@odctl.io / password):
  - External (host): http://127.0.0.1:3005
  - Internal (Docker): http://langfuse-web:3000
• OTLP endpoint for traces, over HTTP:
  - External (host): http://127.0.0.1:3005/api/public/otel
  - Internal (Docker): http://langfuse-web:3000/api/public/otel
• Project keys: public key pk-lf-odctl, secret key sk-lf-odctl, sent as
  HTTP Basic auth. Send the header x-langfuse-ingestion-version: 4 so
  Langfuse shows a trace at once, not up to 10 minutes later.
• Starts ch-lite, so it cannot run beside ch-full.
```

| Service           | Image                             | Host:container ports | Memory limit |
| ----------------- | --------------------------------- | -------------------- | ------------ |
| `langfuse-web`    | `langfuse/langfuse:4.72.0`        | `3005:3000`          | `2g`         |
| `langfuse-worker` | `langfuse/langfuse-worker:4.72.0` | none                 | `2g`         |
