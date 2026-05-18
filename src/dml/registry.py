from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from dml.config import get_registry_path


class StackConfig(BaseModel):
    file: str
    description: str
    profiles: List[str]
    capacities: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    parent: Optional[str] = None


class Registry(BaseModel):
    capacities: Dict[str, str]
    stacks: Dict[str, StackConfig]


def load_registry() -> Registry:
    """Loads and validates the registry.yml file from the active directory."""
    path = get_registry_path()

    if not path.exists():
        raise FileNotFoundError(f"Registry file not found at {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return Registry(**data)
