# Python from docs/guides/mlflow.md. .github/scripts/smoke.sh runs each section
# on the host, with the MLflow and XGBoost versions the server uses.

# --8<-- [start:log-run]
import pathlib
import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:5004")
mlflow.set_experiment("demo")

p = pathlib.Path("notes.txt")
p.write_text("hello")
with mlflow.start_run() as run:
    mlflow.log_param("k", "v")
    mlflow.log_metric("m", 1.0)
    mlflow.log_artifact(str(p))

print(mlflow.get_run(run.info.run_id).info.artifact_uri)
print([f.path for f in mlflow.MlflowClient().list_artifacts(run.info.run_id)])
# --8<-- [end:log-run]

# --8<-- [start:register-model]
import mlflow, numpy as np, xgboost as xgb
from mlflow import MlflowClient

mlflow.set_tracking_uri("http://127.0.0.1:5004")
mlflow.set_experiment("demo-model")

X, y = np.array([[0.0], [1.0], [2.0], [3.0]]), np.array([0, 0, 1, 1])
with mlflow.start_run():
    model = xgb.XGBClassifier(n_estimators=5, max_depth=2).fit(X, y)
    mlflow.xgboost.log_model(model, name="model", registered_model_name="demo-model")

client = MlflowClient()
version = max(int(mv.version) for mv in client.search_model_versions("name='demo-model'"))
client.set_registered_model_alias("demo-model", "champion", version)
# --8<-- [end:register-model]

# --8<-- [start:download]
import os

os.environ["MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD"] = "false"
import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:5004")
path = mlflow.artifacts.download_artifacts("models:/demo-model@champion")
print(sorted(os.listdir(path)))
# --8<-- [end:download]

# --8<-- [start:features-model]
import mlflow, pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature

mlflow.set_tracking_uri("http://127.0.0.1:5004")
mlflow.set_experiment("driver-score")
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        name="model",
        python_model="driver_score.py",
        pip_requirements=["requests"],
        signature=infer_signature(pd.DataFrame({"driver_id": [1001]}), [1]),
        registered_model_name="driver-score",
    )

client = MlflowClient()
version = max(int(mv.version) for mv in client.search_model_versions("name='driver-score'"))
client.set_registered_model_alias("driver-score", "champion", version)
# --8<-- [end:features-model]
