import numpy as np
import pandas as pd
import pendulum
from airflow.sdk import DAG, Param, task
from evidently import Report
from evidently.metrics import ValueDrift

# The Wasserstein distance is in units of the reference column's standard
# deviation. A run fails when the distance passes this value.
DRIFT_THRESHOLD = 0.5

with DAG(
    dag_id="drift_check",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    # How far the current data's mean has moved from the reference's, in standard deviations.
    params={"shift": Param(3.0, type="number")},
):

    @task
    def check_drift(params=None):
        """Fail the run when column x of the current data has drifted from the reference.

        Args:
            params: The run's parameters. `shift` moves the current data's mean.

        Raises:
            ValueError: When the Wasserstein distance is above DRIFT_THRESHOLD.
        """
        reference = pd.DataFrame({"x": np.random.default_rng(7).normal(0, 1, 500)})
        current = pd.DataFrame(
            {"x": np.random.default_rng(8).normal(params["shift"], 1, 500)}
        )
        report = Report([ValueDrift(column="x", method="wasserstein")])
        result = report.run(current_data=current, reference_data=reference)
        distance = result.dict()["metrics"][0]["value"]
        print(f"Wasserstein distance of x: {distance:.2f}, threshold {DRIFT_THRESHOLD}")
        if distance > DRIFT_THRESHOLD:
            raise ValueError(f"x drifted: {distance:.2f} is above {DRIFT_THRESHOLD}")

    check_drift()
