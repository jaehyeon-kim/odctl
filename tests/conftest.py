import pytest

from odctl.registry import Registry, StackConfig


@pytest.fixture
def mock_registry_data():
    """Provides a valid, minimal Registry structure for testing."""
    return Registry(
        stacks={
            "infra": StackConfig(
                file="compose-infra.yml",
                description="Core infrastructure",
                profiles=["storage", "kafka"],
                depends_on={"storage": [], "kafka": []},
            ),
            "spark": StackConfig(
                file="compose-spark.yml",
                description="Spark compute layer",
                profiles=["spark-master", "spark-worker"],
                depends_on={"spark-master": ["storage"], "spark-worker": ["storage"]},
            ),
        },
    )


@pytest.fixture
def mock_workspace(tmp_path, monkeypatch):
    """Mocks workspace directories to use an isolated temporary path."""
    monkeypatch.setattr("odctl.config.get_workspace_dir", lambda: tmp_path / ".odctl")
    monkeypatch.setattr(
        "odctl.config.get_internal_resources_dir", lambda: tmp_path / "resources"
    )

    # Create the fake directories
    (tmp_path / ".odctl").mkdir(parents=True, exist_ok=True)
    (tmp_path / "resources").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture(autouse=True)
def _no_tag_in_environment(monkeypatch):
    """CLI commands set TAG in the process when there is no workspace (#127).
    Each test starts without it, and monkeypatch restores the original after."""
    monkeypatch.delenv("TAG", raising=False)
