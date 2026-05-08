from pathlib import Path

# The internal immutable resources bundled with the CLI
INTERNAL_RESOURCES_DIR = Path(__file__).parent.resolve() / "resources"


def get_workspace_dir() -> Path:
    """The local mutable workspace."""
    return Path.cwd() / ".dml"


def get_active_dir() -> Path:
    """Returns the local workspace if it exists, otherwise falls back to internal resources."""
    workspace = get_workspace_dir()
    return workspace if workspace.exists() else INTERNAL_RESOURCES_DIR


def get_registry_path() -> Path:
    return get_active_dir() / "registry.yaml"


def get_compose_path(filename: str) -> Path:
    return get_active_dir() / filename
