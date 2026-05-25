import pytest

from dml.registry import Registry, StackConfig


@pytest.fixture
def mock_registry_data():
    """Provides a valid, minimal Registry structure for testing."""
    return Registry(
        capacities={"compute": "spark", "messaging": "kafka"},
        stacks={
            "infra": StackConfig(
                file="compose-infra.yml",
                description="Core infrastructure",
                profiles=["storage", "kafka"],
                capacities=["messaging"],
                depends_on=[],
            ),
            "spark": StackConfig(
                file="compose-spark.yml",
                description="Spark compute layer",
                profiles=["spark-master", "spark-worker"],
                capacities=["compute"],
                depends_on=["storage"],
            ),
        },
    )


@pytest.fixture
def mock_workspace(tmp_path, monkeypatch):
    """Mocks workspace directories to use an isolated temporary path."""
    monkeypatch.setattr("dml.config.get_workspace_dir", lambda: tmp_path / ".dml")
    monkeypatch.setattr(
        "dml.config.get_internal_resources_dir", lambda: tmp_path / "resources"
    )

    # Create the fake directories
    (tmp_path / ".dml").mkdir(parents=True, exist_ok=True)
    (tmp_path / "resources").mkdir(parents=True, exist_ok=True)
    return tmp_path
