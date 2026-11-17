# Observability

## Telemetry (grafana/otel-lgtm)

Profiles: `telemetry`. Stack `obsv`, defined in `compose-obsv.yml`.

### telemetry

Depends on: `deps`. `odctl up telemetry` also starts: `deps`.

```text
• Prometheus Time Series Engine (also takes OTLP at /api/v1/otlp/v1/metrics):
  * External (host): http://127.0.0.1:19090
  * Internal (Docker): http://prometheus:9090
• Grafana Dashboards (Credentials: user / password):
  * External (host): http://127.0.0.1:3004
  * Internal (Docker): http://grafana:3000
  * A dashboard per service in the odctl folder, which fills in once
    that service's profile is up.
• OTLP Receiver (metrics, traces and logs):
  * External (host): 127.0.0.1:4317 (gRPC), http://127.0.0.1:4318 (HTTP)
  * Internal (Docker): otel-lgtm:4317 (gRPC), http://otel-lgtm:4318 (HTTP)
```

| Service     | Image                      | Host:container ports                                | Memory limit |
| ----------- | -------------------------- | --------------------------------------------------- | ------------ |
| `otel-lgtm` | `grafana/otel-lgtm:0.37.0` | `19090:9090`, `3004:3000`, `4317:4317`, `4318:4318` | `2g`         |
