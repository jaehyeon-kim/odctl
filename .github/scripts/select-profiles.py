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
the mapping is not repeated, except the profiles a group's case starts from
another file, listed in ALSO_RUNS.

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
    # feast brings up postgres, storage, catalog and valkey with it, and its
    # assertion installs a client to prove the offline and online halves work.
    "feast",
    # evidently brings up postgres and storage, and its assertion round-trips a
    # dataset through SeaweedFS as well as a report through Postgres.
    "evidently",
    "lineage",
    "telemetry",
    "metadata",
    # The part before the colon is the profile to start. metadata:deps and
    # metadata:autopilot start the same profile as metadata. Each examples group
    # recreates metadata twice, which is why each runs alone, in parallel with the others.
    "metadata:deps",
    "metadata:autopilot",
    "airflow",
    "temporal",
    "postgres",
    "storage",
    "catalog",
    "valkey",
]

# A change to any of these can break any profile, so do not narrow the matrix.
RUN_EVERYTHING = (
    "src/odctl/",
    ".github/scripts/smoke.sh",
    ".github/scripts/spark_avro_producer.py",
    ".github/scripts/select-profiles.py",
    ".github/workflows/",
)

# Except these, which live under src/odctl/ but only describe one profile each.
# Handled separately so a single compose edit does not run the whole matrix.
COMPOSE_PREFIX = "src/odctl/resources/compose-"

REGISTRY = Path("src/odctl/resources/registry.yml")

# smoke.sh starts some profiles from another group's case: the kafka case starts
# catalog, the flink case starts kafka-lite and feast, the spark case starts
# kafka-lite, the fluss and feast cases start flink-lite, and the airflow case
# starts feast. A change to that compose file needs these groups as well as the
# ones the registry maps to it.
ALSO_RUNS = {
    "compose-infra.yml": ["kafka-lite kafka-full"],
    "compose-kafka.yml": ["flink-lite flink-full", "spark-lite spark-full"],
    "compose-flink.yml": ["fluss", "feast"],
    "compose-mlops.yml": ["flink-lite flink-full", "airflow"],
}

# smoke.sh runs the guide commands in docs/snippets/<guide>/, so a change there
# needs the groups whose assertions run that guide. A folder missing from this
# map runs everything, and a test fails until it is added.
SNIPPET_PREFIX = "docs/snippets/"
SNIPPET_GROUPS = {
    "getting-started": ["kafka-lite kafka-full"],
    "how-it-works": [
        "storage",
        "catalog",
        "trino",
        "airflow",
        "mlflow",
        "metadata:deps",
        "metadata:autopilot",
    ],
    "kafka": ["kafka-lite kafka-full"],
    "kafka-connect": ["kafka-lite kafka-full"],
    "iceberg-ingestion": ["kafka-lite kafka-full", "flink-lite flink-full"],
    "flink-sql": ["flink-lite flink-full"],
    "rolling-windows": ["flink-lite flink-full"],
    "fluss": ["fluss"],
    "spark": ["spark-lite spark-full"],
    "clickhouse": ["ch-lite ch-full"],
    "trino-metabase": ["trino", "metabase"],
    "hybrid-search": ["postgres"],
    "valkey": ["valkey"],
    "airflow-dags": ["airflow"],
    "temporal-workers": ["temporal"],
    "mlflow": ["mlflow"],
    "feast-iceberg": ["feast", "flink-lite flink-full", "mlflow", "airflow"],
    "feast-vector-retrieval": ["feast"],
    "evidently-reports": ["evidently"],
    "lineage": ["lineage"],
    "openmetadata": ["metadata", "metadata:autopilot"],
    "telemetry": ["telemetry"],
}


def _profile_to_file(registry_path: Path = REGISTRY) -> dict:
    """
    Map each profile to the compose file the registry says provides it.

    Args:
        registry_path (Path): The registry.yml to read.

    Returns:
        dict: The compose file name of each profile.
    """
    data = yaml.safe_load(registry_path.read_text())
    mapping = {}
    for stack in data["stacks"].values():
        for profile in stack["profiles"]:
            mapping[profile] = stack["file"]
    return mapping


def select(changed: list, registry_path: Path = REGISTRY) -> list:
    """
    Return the profile groups that the changed files require.

    Args:
        changed (list): The paths of the changed files, relative to the repository.
        registry_path (Path): The registry.yml that maps profiles to compose files.

    Returns:
        list: The groups to run, every group when a change affects them all, or none.
    """
    changed = [c for c in changed if c.strip()]
    if not changed:
        return []

    def is_compose(path: str) -> bool:
        """
        Tell whether a path is one of odctl's compose files.

        Args:
            path (str): A changed file's path, relative to the repository.

        Returns:
            bool: True when the path is under the compose files' folder.
        """
        return path.startswith(COMPOSE_PREFIX)

    broad = [
        c
        for c in changed
        if any(c.startswith(prefix) for prefix in RUN_EVERYTHING) and not is_compose(c)
    ]
    if broad:
        return list(GROUPS)

    snippet_groups = set()
    for c in changed:
        if c.startswith(SNIPPET_PREFIX):
            guide = c[len(SNIPPET_PREFIX) :].split("/")[0]
            if guide not in SNIPPET_GROUPS:
                return list(GROUPS)
            snippet_groups.update(SNIPPET_GROUPS[guide])

    mapping = _profile_to_file(registry_path)
    touched_files = {Path(c).name for c in changed if is_compose(c)}

    selected = []
    for group in GROUPS:
        # A group name may carry a suffix after a colon, as metadata:deps does.
        files = {mapping.get(p.split(":")[0]) for p in group.split()}
        also = any(group in ALSO_RUNS.get(name, []) for name in touched_files)
        if files & touched_files or group in snippet_groups or also:
            selected.append(group)
    return selected


def main() -> None:
    """Print the groups for the files named on the command line, or every group with `--all`, as JSON."""
    args = sys.argv[1:]
    if "--all" in args:
        print(json.dumps(list(GROUPS)))
        return
    print(json.dumps(select(args)))


if __name__ == "__main__":
    main()
