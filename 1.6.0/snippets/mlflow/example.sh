#!/usr/bin/env bash
# Starts mlflow, logs a run with an artifact, registers an XGBoost model with
# the alias champion, serves it with mlflow-serve and scores two rows. Run it
# in the folder that holds your .odctl workspace, in an environment with
# mlflow==3.16.1 and xgboost 3.2 installed.
set -euo pipefail

odctl up mlflow

python - <<'PY'
import pathlib
import mlflow, numpy as np, xgboost as xgb
from mlflow import MlflowClient

mlflow.set_tracking_uri("http://127.0.0.1:5004")

mlflow.set_experiment("demo")
p = pathlib.Path("notes.txt")
p.write_text("hello")
with mlflow.start_run() as run:
    mlflow.log_param("k", "v")
    mlflow.log_metric("m", 1.0)
    mlflow.log_artifact(str(p))
print(mlflow.get_run(run.info.run_id).info.artifact_uri)

mlflow.set_experiment("demo-model")
X, y = np.array([[0.0], [1.0], [2.0], [3.0]]), np.array([0, 0, 1, 1])
with mlflow.start_run():
    model = xgb.XGBClassifier(n_estimators=5, max_depth=2).fit(X, y)
    mlflow.xgboost.log_model(model, name="model", registered_model_name="demo-model")
client = MlflowClient()
version = max(int(mv.version) for mv in client.search_model_versions("name='demo-model'"))
client.set_registered_model_alias("demo-model", "champion", version)
PY

# Serve the champion: set MODEL_URI in the workspace and replace the containers.
sed -i.bak 's|^MODEL_URI=.*|MODEL_URI="models:/demo-model@champion"|' .odctl/.env
odctl recreate mlflow
curl -s -X POST http://127.0.0.1:5003/invocations \
  -H 'Content-Type: application/json' -d '{"inputs": [[0.0], [3.0]]}'
echo
