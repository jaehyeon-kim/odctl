from typing import Dict, List, Set

import typer
from rich.console import Console

from dml.registry import load_registry

console = Console()


def get_profile_map() -> Dict[str, dict]:
    """Creates a reverse lookup mapping a profile back to its stack config."""
    registry = load_registry()
    profile_map = {}
    for stack_id, config in registry.stacks.items():
        for profile in config.profiles:
            profile_map[profile] = {"stack_id": stack_id, "file": config.file}
    return profile_map


def validate_profiles(profiles: List[str], profile_map: Dict[str, dict]):
    """Checks if requested profiles exist in the registry."""
    invalid = [p for p in profiles if p not in profile_map]
    if invalid:
        console.print(
            f"[bold red]Error:[/bold red] Unknown profiles: {', '.join(invalid)}"
        )
        raise typer.Exit(1)


def resolve_dependencies(
    requested_profiles: List[str], profile_map: Dict[str, dict], registry
) -> Set[str]:
    """Traverses the dependency graph to ensure all required profiles are included."""
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
    profiles: List[str] = None, all_profiles: bool = False, resolve_deps: bool = True
) -> Dict[str, List[str]]:
    """Generates a mapping of compose files to the profiles that need to be run."""
    registry = load_registry()
    profile_map = get_profile_map()
    execution_plan = {}

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
