"""The mlflow service's settings that its own job workers depend on.

Nothing here needs Docker.
"""

import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()


def _mlflow():
    return yaml.safe_load((RESOURCES / "compose-mlops.yml").read_text())["services"]["mlflow"]


def test_job_workers_call_the_gateway_at_an_allowed_host():
    # Automatic evaluation runs gateway:/ judges in the server's job workers,
    # which call MLFLOW_GATEWAY_URI. The server's own default is
    # http://0.0.0.0:5000, which --allowed-hosts refuses.
    gateway = _mlflow()["environment"]["MLFLOW_GATEWAY_URI"]
    command = " ".join(_mlflow()["command"])
    allowed = command.split("--allowed-hosts", 1)[1].split()[0].split(",")
    assert gateway == "http://127.0.0.1:5000"
    assert gateway.removeprefix("http://") in allowed
