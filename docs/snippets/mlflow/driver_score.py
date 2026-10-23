import mlflow
import requests


class DriverScore(mlflow.pyfunc.PythonModel):
    """Scores a driver 1 when the online store holds a conversion rate above 0.5."""

    def predict(self, context, model_input, params=None):
        reply = requests.post(
            "http://feast-serve:6566/get-online-features",
            json={
                "features": ["driver_stats:conv_rate"],
                "entities": {"driver_id": [int(i) for i in model_input["driver_id"]]},
            },
            timeout=10,
        ).json()
        names = reply["metadata"]["feature_names"]
        rates = reply["results"][names.index("conv_rate")]["values"]
        return [int(rate is not None and rate > 0.5) for rate in rates]


mlflow.models.set_model(DriverScore())
