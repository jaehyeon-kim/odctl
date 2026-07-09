from typing import Dict, List, Optional, Set

import typer
from rich.console import Console

from odctl.registry import load_registry

console = Console()


def get_profile_map() -> Dict[str, dict]:
    """
    Create a reverse lookup mapping a profile back to its stack configuration.

    Returns:
        Dict[str, dict]: A dictionary where keys are profile names and values contain
        the associated 'stack_id' and 'file'.
    """
    registry = load_registry()
    profile_map = {}
    for stack_id, config in registry.stacks.items():
        for profile in config.profiles:
            profile_map[profile] = {"stack_id": stack_id, "file": config.file}
    return profile_map


def validate_profiles(profiles: List[str], profile_map: Dict[str, dict]):
    """
    Check if requested profiles exist in the registry.

    Args:
        profiles (List[str]): The list of requested profile names.
        profile_map (Dict[str, dict]): The map of valid profiles.

    Raises:
        typer.Exit: If any requested profile is not found in the profile map.
    """
    invalid = [p for p in profiles if p not in profile_map]
    if invalid:
        console.print(
            f"[bold red]Error:[/bold red] Unknown profiles: {', '.join(invalid)}"
        )
        raise typer.Exit(1)


def resolve_dependencies(
    requested_profiles: List[str], profile_map: Dict[str, dict], registry
) -> Set[str]:
    """
    Traverse the dependency graph to ensure all required profiles are included.

    Args:
        requested_profiles (List[str]): The initial set of profiles requested by the user.
        profile_map (Dict[str, dict]): The reverse lookup map of profiles.
        registry: The loaded stack registry.

    Returns:
        Set[str]: A complete set of profile names, including all upstream dependencies.
    """
    resolved = set(requested_profiles)
    queue = list(requested_profiles)

    while queue:
        current = queue.pop(0)
        stack_id = profile_map[current]["stack_id"]
        stack = registry.stacks[stack_id]
        for dep in stack.depends_on:
            if dep not in resolved:
                resolved.add(dep)
                queue.append(dep)
    return resolved


def build_execution_plan(
    profiles: Optional[List[str]] = None,
    all_profiles: bool = False,
    resolve_deps: bool = True,
) -> Dict[str, List[str]]:
    """
    Generate a mapping of compose files to the profiles that need to be run.

    This function resolves parent dependencies and applies a lightweight topological sort
    so infrastructure layers are grouped before target execution layers.

    Args:
        profiles (List[str], optional): Specific profiles to execute. Defaults to None.
        all_profiles (bool, optional): If True, targets all available profiles in the registry. Defaults to False.
        resolve_deps (bool, optional): If True, traverses the registry to include dependencies. Defaults to True.

    Returns:
        Dict[str, List[str]]: A dictionary mapping compose filenames to lists of target profiles.

    Raises:
        typer.Exit: If no profiles are provided and `all_profiles` is False, or if validation fails.
    """
    registry = load_registry()
    profile_map = get_profile_map()
    execution_plan: Dict[str, List[str]] = {}

    if all_profiles:
        # For teardown/pull all: group all profiles by file
        for stack_id, config in registry.stacks.items():
            if config.file not in execution_plan:
                execution_plan[config.file] = []
            execution_plan[config.file].extend(config.profiles)
        return execution_plan

    if not profiles:
        console.print(
            "[bold red]Error:[/bold red] Please specify profile names or use --all"
        )
        raise typer.Exit(1)

    validate_profiles(profiles, profile_map)

    if resolve_deps:
        final_profiles = resolve_dependencies(profiles, profile_map, registry)
    else:
        final_profiles = set(profiles)

    # Enforce lightweight topological sort (deps -> base -> target)
    order_weights = {"deps": 0, "base": 1}
    sorted_profiles = sorted(
        list(final_profiles), key=lambda p: (order_weights.get(p, 99), p)
    )

    for p in sorted_profiles:
        file = profile_map[p]["file"]
        if file not in execution_plan:
            execution_plan[file] = []
        execution_plan[file].append(p)

    return execution_plan
