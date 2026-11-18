from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, model_validator

from odctl.config import UnreadableFileError, get_registry_path, read_yaml


class StackConfig(BaseModel):
    """
    Pydantic model representing a single stack configuration within the registry.

    Attributes:
        file (str): The docker-compose filename.
        description (str): A brief description of the stack's purpose.
        profiles (List[str]): A list of compose profiles provided by this stack.
        depends_on (List[str]): Other stack profiles required for this stack to function.
        parent (Optional[str]): An optional grouping identifier.
        role (Optional[str]): A detailed explanation of the stack's architectural role.
        usage (Optional[Union[str, Dict[str, str]]]): Usage instructions, which can be a
            single string or a dictionary mapping profile names to specific instructions.
    """

    file: str
    description: str
    profiles: List[str]
    depends_on: Dict[str, List[str]] = Field(default_factory=dict)
    parent: Optional[str] = None
    role: Optional[str] = None
    usage: Optional[Union[str, Dict[str, str]]] = None


class Registry(BaseModel):
    """
    Pydantic model representing the entire `registry.yml` configuration.

    Attributes:
        stacks (Dict[str, StackConfig]): A map of stack IDs to their configurations.
    """

    stacks: Dict[str, StackConfig]

    @model_validator(mode="after")
    def _profiles_resolve(self) -> "Registry":
        """
        Check that every profile and dependency names one profile of one stack.

        The planner maps a profile to one stack and reads its dependencies from that
        stack, so a profile under two stacks went to the last one, a `depends_on`
        key of another stack's profile was never read, and a dependency that no
        stack lists raised KeyError while the plan was built. A profile listed twice
        in one stack is refused with a message that names that stack once.

        Returns:
            Registry: The registry, unchanged.

        Raises:
            ValueError: Naming the first entry that breaks one of these rules.
        """
        owner: Dict[str, str] = {}
        for stack_id, stack in self.stacks.items():
            for profile in stack.profiles:
                if owner.get(profile) == stack_id:
                    raise ValueError(
                        f"the stack '{stack_id}' lists the profile '{profile}' twice."
                    )
                if profile in owner:
                    raise ValueError(
                        f"the profile '{profile}' is listed under the stacks "
                        f"'{owner[profile]}' and '{stack_id}'."
                    )
                owner[profile] = stack_id
        for stack_id, stack in self.stacks.items():
            for profile, dependencies in stack.depends_on.items():
                if profile not in stack.profiles:
                    raise ValueError(
                        f"the stack '{stack_id}' lists dependencies for '{profile}', "
                        "which is not one of its profiles."
                    )
                for dependency in dependencies:
                    if dependency not in owner:
                        raise ValueError(
                            f"the profile '{profile}' depends on '{dependency}', "
                            "which no stack lists."
                        )
        return self


def load_registry() -> Registry:
    """
    Load and validate the `registry.yml` file from the active directory.

    Returns:
        Registry: A validated Pydantic model containing the entire stack configuration.

    Raises:
        UnreadableFileError: As `Cannot read <path>: <reason>`, when the file is missing, is not
            valid YAML, or is not a registry, such as an empty file or a stack with no
            `file`.
    """
    path = get_registry_path()
    data = read_yaml(path, str(path))
    if not isinstance(data, dict):
        raise UnreadableFileError(
            f"Cannot read {path}: its top level is not a mapping."
        )
    try:
        return Registry.model_validate(data)
    except ValidationError as e:
        reasons = []
        for error in e.errors():
            where = ".".join(str(part) for part in error["loc"])
            # A check of `Registry` itself raises ValueError, which pydantic reports
            # as "Value error, <message>"; its own message names the entry.
            cause = error.get("ctx", {}).get("error")
            reason = str(cause) if isinstance(cause, ValueError) else error["msg"]
            reasons.append(f"{where}: {reason}" if where else reason)
        raise UnreadableFileError(f"Cannot read {path}: {'; '.join(reasons)}") from e
