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
        for dep in stack.depends_on.get(current, []):
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

    # Enforce lightweight topological sort
    order_weights = {"deps": 0, "postgres": 1, "storage": 1, "catalog": 2}
    sorted_profiles = sorted(
        list(final_profiles), key=lambda p: (order_weights.get(p, 99), p)
    )

    for p in sorted_profiles:
        file = profile_map[p]["file"]
        if file not in execution_plan:
            execution_plan[file] = []
        execution_plan[file].append(p)

    return execution_plan


def expand_same_file_dependencies(
    file_profiles: List[str], active: List[str]
) -> List[str]:
    """Widen a set of active profiles to include their same-file dependencies.

    Compose filters services by the active profiles and then validates
    depends_on against what survives, so activating a profile whose service
    depends on one in another profile of the same file gives "depends on
    undefined service" and the command aborts. Teardown selects profiles by
    running state and by volume ownership, which can pick one profile of a file
    on its own, so it has to widen the selection back to a valid project.

    Only same-file dependencies are added. Each file is torn down by its own
    compose call, and widening across files would stop shared infrastructure
    that other profiles may still be using.

    Args:
        file_profiles (List[str]): Every profile the compose file declares.
        active (List[str]): The profiles selected for this file.

    Returns:
        List[str]: The selected profiles plus their same-file dependencies, in
            the order the file declares them.
    """
    registry = load_registry()
    profile_map = get_profile_map()

    in_file = set(file_profiles)
    selected = set(active)
    queue = list(active)
    while queue:
        current = queue.pop(0)
        entry = profile_map.get(current)
        if not entry:
            continue
        stack = registry.stacks[entry["stack_id"]]
        for dep in stack.depends_on.get(current, []):
            if dep in in_file and dep not in selected:
                selected.add(dep)
                queue.append(dep)
    return [p for p in file_profiles if p in selected]


def expand_plan_dependencies(plan: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Widen every file in a plan to include its same-file dependencies.

    Any command that hands profiles to a compose client has to pass a set that
    validates, because compose filters services by active profile and then
    checks depends_on against what survives. Naming a profile whose service
    depends on one in another profile of the same file therefore aborts with
    "depends on undefined service", and that applies to teardown, ps, logs and
    restart alike, not just to teardown of a whole file.

    Plans built with ``resolve_deps=False`` need this. Plans built with
    ``resolve_deps=True`` already carry their dependencies.

    Args:
        plan (Dict[str, List[str]]): Compose file to selected profiles.

    Returns:
        Dict[str, List[str]]: Same mapping, each selection widened to a set
            compose will accept, in the order each file declares.
    """
    declared = build_execution_plan(None, all_profiles=True, resolve_deps=False)
    return {
        file: expand_same_file_dependencies(declared.get(file, profiles), profiles)
        for file, profiles in plan.items()
    }
