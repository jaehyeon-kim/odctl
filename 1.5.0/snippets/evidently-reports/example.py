"""Pushes a data drift report to Evidently, stores a dataset and reads it back.

Start the profile with `odctl up evidently` and install the client with
`pip install evidently==0.7.23 "pandas<3.1"` first.
"""

import numpy as np
import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset
from evidently.ui.workspace import RemoteWorkspace

ws = RemoteWorkspace("http://127.0.0.1:8089")
project = ws.create_project("demo-example")

# Column x moves by three standard deviations and y does not.
rng = np.random.default_rng(7)
reference = pd.DataFrame({"x": rng.normal(0, 1, 500), "y": rng.normal(0, 1, 500)})
current = pd.DataFrame({"x": rng.normal(3, 1, 500), "y": rng.normal(0, 1, 500)})
snapshot = Report([DataDriftPreset()]).run(current_data=current, reference_data=reference)
ws.add_run(project.id, snapshot)
print(f"report pushed to project {project.id}")

data = pd.DataFrame({"id": [1, 2, 3], "score": [0.1, 0.5, 0.9]})
dataset = Dataset.from_pandas(data, data_definition=DataDefinition())
dataset_id = ws.add_dataset(project.id, dataset, "demo")
print(ws.load_dataset(dataset_id).as_dataframe())
