from odctl.config import (
    get_active_dir,
    get_compose_path,
    get_internal_resources_dir,
    get_registry_path,
)


def test_active_dir_fallback_to_internal(mock_workspace, monkeypatch):
    """Should use internal resources if local workspace doesn't exist yet."""
    # Remove the local .odctl workspace created by the fixture
    workspace_dir = mock_workspace / ".odctl"
    if workspace_dir.exists():
        workspace_dir.rmdir()

    # Assert it gracefully falls back to the real internal resources directory
    assert get_active_dir() == get_internal_resources_dir()


def test_active_dir_uses_workspace(mock_workspace):
    """Should prefer local .odctl workspace if it exists."""
    workspace_dir = mock_workspace / ".odctl"
    assert get_active_dir() == workspace_dir


def test_get_registry_path(mock_workspace):
    """Validates registry path updates dynamically based on active directory."""
    expected_path = mock_workspace / ".odctl" / "registry.yml"
    assert get_registry_path() == expected_path


def test_get_compose_path(mock_workspace):
    """Validates file-specific paths generation."""
    expected_path = mock_workspace / ".odctl" / "compose-spark.yml"
    assert get_compose_path("compose-spark.yml") == expected_path
