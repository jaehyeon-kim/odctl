# MLOps

## MLflow

Profiles: `mlflow`. Stack `mlops`, defined in `compose-mlops.yml`.

### mlflow

Depends on: `postgres`, `storage`. `odctl up mlflow` also starts: `deps`, `postgres`, `storage`.

```text
• MLflow Tracking UI & Artifact Registry Server:
  * External (host): http://127.0.0.1:5004
  * Internal (Docker): http://mlflow:5000
• MLflow Model Scoring Server, idle until MODEL_URI in .env names a model;
  run `odctl up mlflow` again after setting it. It loads the model once,
  when it starts, so a new version behind the same alias needs
  `odctl restart mlflow`, and the server answers nothing for about 16 seconds:
  * External (host): http://127.0.0.1:5003/invocations
  * Internal (Docker): http://mlflow-serve:5003/invocations
• Liveness: http://127.0.0.1:5003/ping and http://127.0.0.1:5003/health
```

| Service        | Image                                             | Host:container ports | Memory limit |
| -------------- | ------------------------------------------------- | -------------------- | ------------ |
| `mlflow`       | `ghcr.io/jaehyeon-kim/odctl/mlflow:<CLI version>` | `5004:5000`          | `2500m`      |
| `mlflow-serve` | `ghcr.io/jaehyeon-kim/odctl/mlflow:<CLI version>` | `5003:5003`          | `1500m`      |

## Feast

Profiles: `feast`. Stack `mlops`, defined in `compose-mlops.yml`.

### feast

Depends on: `catalog`, `valkey`. `odctl up feast` also starts: `catalog`, `deps`, `postgres`, `storage`, `valkey`.

```text
• Feast UI (registry browser, not data):
  * External (host): http://127.0.0.1:8890
  * Internal (Docker): http://feast-ui:8888
• Upload your feature repository to s3://feast/repo. The services check
  it every 15 seconds and restart Feast when it changes. Run
  `feast apply` from your own environment. odctl ships no definitions.
• Your environment needs: feast[duckdb,iceberg,redis,postgres]
• On an IcebergSource against catalog, pass warehouse="" and
  catalog_name="odctl". The REST client puts warehouse in the URL path,
  and Iceberg's REST fixture server serves the spec with no prefix.
• Online feature server for get_online_features:
  * External (host): http://127.0.0.1:6566
  * Internal (Docker): http://feast-serve:6566
• MCP endpoint, for agents that list Feast's tools and read features:
  http://127.0.0.1:6566/mcp
• Liveness: http://127.0.0.1:6566/health
```

| Service       | Image                                    | Host:container ports | Memory limit |
| ------------- | ---------------------------------------- | -------------------- | ------------ |
| `feast-ui`    | `quay.io/feastdev/feature-server:0.66.0` | `8890:8888`          | `1g`         |
| `feast-serve` | `quay.io/feastdev/feature-server:0.66.0` | `6566:6566`          | `1g`         |

## Evidently

Profiles: `evidently`. Stack `mlops`, defined in `compose-mlops.yml`.

### evidently

Depends on: `postgres`. `odctl up evidently` also starts: `deps`, `postgres`.

```text
• Evidently UI & API (no login, and writes are open):
  * External (host): http://127.0.0.1:8089
  * Internal (Docker): http://evidently:8000
• Push reports with RemoteWorkspace("http://127.0.0.1:8089") from the
  host, or RemoteWorkspace("http://evidently:8000") from a container.
  Reports are computed by the client, so it needs evidently==0.7.23 and pandas<3.1.
  In Airflow, set _AIRFLOW_PIP_DEPS="evidently==0.7.23" in .env.
• Projects, reports, dashboards and datasets: the evidently database
  on Postgres.
• Settings: evidently/config.yaml in the workspace.
```

| Service     | Image                                | Host:container ports | Memory limit |
| ----------- | ------------------------------------ | -------------------- | ------------ |
| `evidently` | `evidently/evidently-service:0.7.23` | `8089:8000`          | `1g`         |
