from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field

from odctl.config import get_registry_path


class StackConfig(BaseModel):
    """
    Pydantic model representing a single stack configuration within the registry.

    Attributes:
        file (str): The docker-compose filename.
        description (str): A brief description of the stack's purpose.
        profiles (List[str]): A list of compose profiles provided by this stack.
        capacities (List[str]): Semantic tags mapping to the stack's capabilities.
        depends_on (List[str]): Other stack profiles required for this stack to function.
        parent (Optional[str]): An optional grouping identifier.
        role (Optional[str]): A detailed explanation of the stack's architectural role.
        usage (Optional[Union[str, Dict[str, str]]]): Usage instructions, which can be a
            single string or a dictionary mapping profile names to specific instructions.
    """

    file: str
    description: str
    profiles: List[str]
    capacities: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    parent: Optional[str] = None
    role: Optional[str] = None
    usage: Optional[Union[str, Dict[str, str]]] = None


class Registry(BaseModel):
    """
    Pydantic model representing the entire `registry.yml` configuration.

    Attributes:
        capacities (Dict[str, str]): A map of broad capability names to specific keywords.
        stacks (Dict[str, StackConfig]): A map of stack IDs to their configurations.
    """

    capacities: Dict[str, str]
    stacks: Dict[str, StackConfig]


def load_registry() -> Registry:
    """
    Load and validate the `registry.yml` file from the active directory.

    Returns:
        Registry: A validated Pydantic model containing the entire stack configuration.

    Raises:
        FileNotFoundError: If the `registry.yml` file does not exist.
    """
    path = get_registry_path()

    if not path.exists():
        raise FileNotFoundError(f"Registry file not found at {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return Registry(**data)
