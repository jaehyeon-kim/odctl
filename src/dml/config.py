from pathlib import Path

# Absolute path resolution
PACKAGE_ROOT = Path(__file__).parent.parent.parent.resolve()
RESOURCES_DIR = PACKAGE_ROOT / "resources"
REGISTRY_PATH = RESOURCES_DIR / "registry.yaml"


def get_compose_path(filename: str) -> Path:
    """Helper to get the absolute path of a compose file."""
    return (RESOURCES_DIR / filename).resolve()
