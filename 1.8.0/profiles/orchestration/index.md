# Orchestration

## Apache Airflow

Profiles: `airflow`. Stack `orch`, defined in `compose-orch.yml`.

### airflow

Depends on: `postgres`, `storage`. `odctl up airflow` also starts: `deps`, `postgres`, `storage`.

```text
• Airflow Web UI (Credentials: user / password):
  * External (host): http://127.0.0.1:8085
  * Internal (Docker): http://airflow:8080
• DAGs: read from s3://airflow/dags every 15 seconds.
• Plugins: copied from s3://airflow/plugins at start. Airflow loads
  plugins only once, so run `odctl restart airflow` after changing one.
```

| Service   | Image                                              | Host:container ports | Memory limit |
| --------- | -------------------------------------------------- | -------------------- | ------------ |
| `airflow` | `ghcr.io/jaehyeon-kim/odctl/airflow:<CLI version>` | `8085:8080`          | `3g`         |

## Temporal

Profiles: `temporal`. Stack `orch`, defined in `compose-orch.yml`.

### temporal

Depends on: `deps`. `odctl up temporal` also starts: `deps`.

```text
• Temporal Web UI:
  * External (host): http://127.0.0.1:8233
  * Internal (Docker): http://temporal:8233
• gRPC endpoint for SDK clients and workers (namespace "default"):
  * External (host): 127.0.0.1:7233
  * Internal (Docker): temporal:7233
• Your environment needs: temporalio. odctl runs only the server, so
  your own process runs the worker that executes workflows and
  activities.
• Development server: the server, the UI and a SQLite database in one
  process. History survives `odctl restart` and is lost on
  `odctl down`, like every odctl service's data.
• Prometheus metrics: http://temporal:9090/metrics, inside the network.
```

| Service    | Image                       | Host:container ports     | Memory limit |
| ---------- | --------------------------- | ------------------------ | ------------ |
| `temporal` | `temporalio/temporal:1.9.1` | `7233:7233`, `8233:8233` | `1g`         |
