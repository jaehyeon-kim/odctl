import yaml
from typing import Dict, List
from pydantic import BaseModel, Field
from dml.config import REGISTRY_PATH


class StackConfig(BaseModel):
    file: str
    description: str
    profiles: List[str]
    capacities: List[str]
    depends_on: List[str] = Field(default_factory=list)


class Registry(BaseModel):
    capacities: Dict[str, str]
    stacks: Dict[str, StackConfig]


def load_registry() -> Registry:
    """Loads and validates the registry.yaml file."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry file not found at {REGISTRY_PATH}")

    with open(REGISTRY_PATH, "r") as f:
        data = yaml.safe_load(f)

    return Registry(**data)
