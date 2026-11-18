import sys
from pathlib import Path
from typing import Any, Optional

import yaml

# Workspace directory requested via the global `--workspace` flag (set in main.py).
_workspace_override: Optional[Path] = None


def set_workspace_override(path: Optional[Path]) -> None:
    """
    Record the workspace directory requested via the global `--workspace` flag.

    Args:
        path (Optional[Path]): The folder given to `--workspace`, or None for the default.
    """
    global _workspace_override
    _workspace_override = path.resolve() if path is not None else None


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
        Path: The directory supplied via `--workspace`, or the `.odctl` directory in
        the current working directory when no override is set.
    """
    if _workspace_override is not None:
        return _workspace_override
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
        filename (str): The name of the compose file (for example, 'compose-infra.yml').

    Returns:
        Path: The path to the requested file within the active directory.
    """
    return get_active_dir() / filename


def read_yaml(path: Path, name: str) -> Any:
    """
    Read a YAML file that odctl needs, such as a compose file or `registry.yml`.

    Args:
        path (Path): The file to read.
        name (str): How the error message names the file.

    Returns:
        Any: The file's content, as PyYAML's `safe_load` gives it.

    Raises:
        ValueError: As `Cannot read <name>: <reason>`, when the file is missing, cannot
            be opened, or is not valid YAML.
    """
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ValueError(f"Cannot read {name}: the file does not exist.") from e
    except OSError as e:
        raise ValueError(f"Cannot read {name}: {e.strerror}.") from e
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark else ""
        raise ValueError(f"Cannot read {name}: it is not valid YAML{where}.") from e
