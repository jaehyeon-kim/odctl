"""The Feast services sync their feature repository from s3://feast/repo.

With nothing there they use the repository bundled with odctl, so the profile
starts before any definitions exist. Nothing here needs Docker.
"""

import yaml

from odctl.config import get_internal_resources_dir


def _compose(name):
    return yaml.safe_load((get_internal_resources_dir() / name).read_text())


def test_feast_services_sync_the_repository_from_s3():
    services = _compose("compose-mlops.yml")["services"]
    for name, verb in (("feast-ui", "ui"), ("feast-serve", "serve")):
        service = services[name]
        command = service["command"]
        assert command[:2] == ["python", "-c"]
        script = command[2]
        assert 'Bucket="feast", Prefix="repo/"' in script
        assert 'shutil.copytree("/bundled_repo", REPO)' in script
        assert "time.sleep(15)" in script and "feast.terminate()" in script
        assert command[3] == verb
        assert service["volumes"] == ["./feast:/bundled_repo:ro"]
        assert service["environment"]["AWS_ACCESS_KEY_ID"] == "${AWS_ACCESS_KEY_ID:-user}"


def test_storage_creates_the_feast_bucket():
    init = next(
        s for s in _compose("compose-infra.yml")["services"].values()
        if "BUCKETS=" in str(s.get("entrypoint", ""))
    )
    assert " feast'" in init["entrypoint"]


def test_airflow_knows_the_feast_registry():
    env = _compose("compose-orch.yml")["services"]["airflow"]["environment"]
    assert env["FEAST_REGISTRY"].endswith("@postgres:5432/feast")


def test_one_profile_starts_both_feast_services():
    services = _compose("compose-mlops.yml")["services"]
    assert services["feast-ui"]["profiles"] == ["feast"]
    assert services["feast-serve"]["profiles"] == ["feast"]


def test_one_profile_starts_mlflow_and_its_model_server():
    services = _compose("compose-mlops.yml")["services"]
    serve = services["mlflow-serve"]
    assert services["mlflow"]["profiles"] == ["mlflow"]
    assert serve["profiles"] == ["mlflow"]
    script = serve["command"][-1]
    assert 'if [ -z "$${MODEL_URI}" ]' in script and "exec sleep infinity" in script
    assert serve["healthcheck"]["test"][1].startswith('[ -z "$${MODEL_URI}" ] ||')
