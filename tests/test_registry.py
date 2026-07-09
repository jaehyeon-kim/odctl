import pytest
from pydantic import ValidationError

from odctl.registry import Registry, load_registry


def test_registry_pydantic_validation(mock_registry_data):
    """Ensures a populated Pydantic model instantiates flawlessly with correct types."""
    assert isinstance(mock_registry_data.capacities, dict)
    assert "infra" in mock_registry_data.stacks
    assert mock_registry_data.stacks["infra"].file == "compose-infra.yml"


def test_registry_validation_missing_fields():
    """Should catch formatting errors if critical keys are dropped from configuration."""
    bad_data = {
        "stacks": {
            "broken-stack": {
                # missing 'file' and 'profiles'
                "description": "Invalid stack configuration"
            }
        }
    }
    with pytest.raises(ValidationError):
        Registry(**bad_data)


def test_load_registry_file_not_found(mock_workspace, monkeypatch):
    """Should raise standard FileNotFoundError if registry file is missing entirely."""
    monkeypatch.setattr(
        "odctl.config.get_registry_path", lambda: mock_workspace / "ghost_registry.yml"
    )
    with pytest.raises(FileNotFoundError):
        load_registry()
