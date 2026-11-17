# Evidently Reports

The `evidently` profile runs the Evidently UI and API. Evidently checks data drift and data quality. Data drift is a change in the distribution of a column between a reference dataset and current data. Your client computes each report and pushes the result to the server. The server keeps projects, reports, dashboards and datasets in the `evidently` database on PostgreSQL. The end-to-end tests run the code below on every release.

This guide builds on [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md).

| Endpoint                       | Address                 |
| ------------------------------ | ----------------------- |
| UI and API from the host       | `http://127.0.0.1:8089` |
| API inside the `odctl` network | `http://evidently:8000` |

Start the profile and install the client:

```bash
odctl up evidently
pip install evidently==0.7.23 "pandas<3.1"
```

The server runs Evidently 0.7.23, so install the same client version. Evidently 0.7.23 fails to import with pandas 3.1, so keep pandas below 3.1. The UI has no login.

## Push a Data Drift Report

This creates the project `demo`, builds a reference dataset and a current one, computes a data drift report and pushes it to the server:

```python
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
```

The code prints nothing. Column `x` moves by three standard deviations and `y` does not, so the report in the UI shows one drifted column.

Open the report under the project's Reports tab:

## Store a Dataset

This stores a small table as a dataset in the same project and reads it back:

```python
from evidently import DataDefinition, Dataset

data = pd.DataFrame({"id": [1, 2, 3], "score": [0.1, 0.5, 0.9]})
dataset_id = ws.add_dataset(project.id, Dataset.from_pandas(data, data_definition=DataDefinition()), "demo")
print(ws.load_dataset(dataset_id).as_dataframe())
```

It prints the dataset read back from the server, with the columns `id` and `score` and three rows. The dataset is stored in the `evidently` database, with the projects and reports.

## Performance Without Outcomes

Evidently gives no estimate of a model's performance while the outcomes are unknown. NannyML gives one. NannyML 0.13.1 supports Python 3.9 to 3.12, and the Airflow image runs Python 3.13. Run NannyML in a Python 3.12 process on your machine instead.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), connect with `RemoteWorkspace("http://evidently:8000")`. For Airflow tasks, set `_AIRFLOW_PIP_DEPS="evidently==0.7.23"` in `.odctl/.env` and run `odctl recreate airflow`. The server's settings are in `evidently/config.yaml` in the workspace.

## Runnable Example

Save this file as `example.py`. Start the profile and install the client as above, then run it with `python example.py`. It creates the project `demo-example`:

```python
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
```

It prints `report pushed to project` with the project's id, and then the dataset with its three rows.
