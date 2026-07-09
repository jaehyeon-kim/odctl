import sys
from pathlib import Path


def get_internal_resources_dir() -> Path:
    """
    Determine the path to the bundled compose files, supporting PyInstaller.

    Returns:
        Path: The absolute path to the internal `resources` directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as a compiled PyInstaller binary
        return Path(sys._MEIPASS) / "odctl" / "resources"
    # Running as a normal Python script
    return Path(__file__).parent.resolve() / "resources"


# Internal immutable resources bundled with the CLI
INTERNAL_RESOURCES_DIR = get_internal_resources_dir()


def get_workspace_dir() -> Path:
    """
    Get the path to the local mutable workspace.

    Returns:
        Path: The absolute path to the `.odctl` directory in the current working directory.
    """
    return Path.cwd() / ".odctl"


def get_active_dir() -> Path:
    """
    Determine the active configuration directory.

    Returns:
        Path: The local workspace directory if it exists; otherwise, falls back
        to the internal resources directory.
    """
    workspace = get_workspace_dir()
    return workspace if workspace.exists() else INTERNAL_RESOURCES_DIR


def get_registry_path() -> Path:
    """
    Get the path to the stack registry configuration file.

    Returns:
        Path: The path to `registry.yml` within the active directory.
    """
    return get_active_dir() / "registry.yml"


def get_compose_path(filename: str) -> Path:
    """
    Get the path to a specific docker-compose file.

    Args:
        filename (str): The name of the compose file (e.g., 'compose-infra.yml').

    Returns:
        Path: The path to the requested file within the active directory.
    """
    return get_active_dir() / filename
