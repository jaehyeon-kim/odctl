# Python from docs/guides/evidently-reports.md. .github/scripts/smoke.sh runs both
# sections in one process, as a reader does, then checks what they stored.

# --8<-- [start:report]
import numpy as np, pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from evidently.ui.workspace import RemoteWorkspace

ws = RemoteWorkspace("http://127.0.0.1:8089")
project = ws.create_project("demo")

rng = np.random.default_rng(7)
reference = pd.DataFrame({"x": rng.normal(0, 1, 500), "y": rng.normal(0, 1, 500)})
current = pd.DataFrame({"x": rng.normal(3, 1, 500), "y": rng.normal(0, 1, 500)})

snapshot = Report([DataDriftPreset()]).run(current_data=current, reference_data=reference)
ws.add_run(project.id, snapshot)
# --8<-- [end:report]

# --8<-- [start:dataset]
from evidently import DataDefinition, Dataset

data = pd.DataFrame({"id": [1, 2, 3], "score": [0.1, 0.5, 0.9]})
dataset_id = ws.add_dataset(project.id, Dataset.from_pandas(data, data_definition=DataDefinition()), "demo")
print(ws.load_dataset(dataset_id).as_dataframe())
# --8<-- [end:dataset]
