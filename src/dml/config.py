import sys
from pathlib import Path


def get_internal_resources_dir() -> Path:
    """Determine the path to the bundled compose files, supporting PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as a compiled PyInstaller binary
        return Path(sys._MEIPASS) / "dml" / "resources"
    # Running as a normal Python script
    return Path(__file__).parent.resolve() / "resources"


# Internal immutable resources bundled with the CLI
INTERNAL_RESOURCES_DIR = get_internal_resources_dir()


def get_workspace_dir() -> Path:
    """The local mutable workspace."""
    return Path.cwd() / ".dml"


def get_active_dir() -> Path:
    """Returns the local workspace if it exists, otherwise falls back to internal resources."""
    workspace = get_workspace_dir()
    return workspace if workspace.exists() else INTERNAL_RESOURCES_DIR


def get_registry_path() -> Path:
    return get_active_dir() / "registry.yml"


def get_compose_path(filename: str) -> Path:
    return get_active_dir() / filename
