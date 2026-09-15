#!/usr/bin/env python3
"""
Choose which e2e profile groups a change needs.

The full matrix pulls roughly 10 GB per entry, so running all of it on every
pull request is not affordable. A change to one compose file only needs the
profiles that file provides. Anything that can affect every profile, the CLI
itself, the registry, the smoke script or the images, still runs everything.

Groups are listed here rather than derived, because the grouping is a decision:
lite and full variants share a large image, so running them together pays for
the pull once. Which compose file each group needs comes from registry.yml, so
the mapping is not repeated.

Usage: select-profiles.py <changed-file>...
       select-profiles.py --all
Prints a JSON array of profile groups to stdout.
"""

import json
import sys
from pathlib import Path

import yaml

GROUPS = [
    # deps has an assertion of its own, and every other group pulls its image
    # anyway, so giving it an entry costs almost nothing.
    "deps",
    "kafka-lite kafka-full",
    "flink-lite flink-full",
    "spark-lite spark-full",
    "ch-lite ch-full",
    "fluss",
    "trino",
    "metabase",
    "mlflow",
    "lineage",
    "telemetry",
    "metadata",
    "airflow",
    "postgres",
    "storage",
    "catalog",
    "valkey",
]

# A change to any of these can break any profile, so do not narrow the matrix.
RUN_EVERYTHING = (
    "src/odctl/",
    ".github/scripts/smoke.sh",
    ".github/scripts/select-profiles.py",
    ".github/workflows/",
)

# Except these, which live under src/odctl/ but only describe one profile each.
# Handled separately so a single compose edit does not run the whole matrix.
COMPOSE_PREFIX = "src/odctl/resources/compose-"

REGISTRY = Path("src/odctl/resources/registry.yml")


def profile_to_file(registry_path: Path = REGISTRY) -> dict:
    """Map each profile to the compose file the registry says provides it."""
    data = yaml.safe_load(registry_path.read_text())
    mapping = {}
    for stack in data["stacks"].values():
        for profile in stack["profiles"]:
            mapping[profile] = stack["file"]
    return mapping


def select(changed: list, registry_path: Path = REGISTRY) -> list:
    """Return the profile groups that the changed files require."""
    changed = [c for c in changed if c.strip()]
    if not changed:
        return []

    def is_compose(path: str) -> bool:
        return path.startswith(COMPOSE_PREFIX)

    broad = [
        c
        for c in changed
        if any(c.startswith(prefix) for prefix in RUN_EVERYTHING) and not is_compose(c)
    ]
    if broad:
        return list(GROUPS)

    mapping = profile_to_file(registry_path)
    touched_files = {Path(c).name for c in changed if is_compose(c)}
    if not touched_files:
        return []

    selected = []
    for group in GROUPS:
        files = {mapping.get(p) for p in group.split()}
        if files & touched_files:
            selected.append(group)
    return selected


def main() -> None:
    args = sys.argv[1:]
    if "--all" in args:
        print(json.dumps(list(GROUPS)))
        return
    print(json.dumps(select(args)))


if __name__ == "__main__":
    main()
