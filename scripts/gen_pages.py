"""
Generate the documentation pages that must match what odctl runs.

mkdocs-gen-files runs this file during every build. It writes one page per technology
in registry.yml, built from the registry and the compose files, and a CLI
reference built from the `--help` output of each command. Neither is kept in
the repository, so a change to the registry, a compose file or a command shows
up in the next build.

The page builders are plain functions so the tests can call them directly.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import yaml

from odctl.config import INTERNAL_RESOURCES_DIR
from odctl.planner import resolve_dependencies
from odctl.registry import Registry, StackConfig

REPO = Path(__file__).resolve().parent.parent

# Compose resolves the images odctl builds with ${TAG:-latest}, and TAG is the
# CLI version once `odctl init` has run.
_TAG_PATTERN = re.compile(r"\$\{TAG(?::?-[^}]*)?\}")
CLI_VERSION_TEXT = "<CLI version>"


def load_registry(resources: Path) -> Registry:
    """Read registry.yml from a resources directory into odctl's own model."""
    return Registry(**yaml.safe_load((resources / "registry.yml").read_text()))


def _profile_map(registry: Registry) -> Dict[str, dict]:
    """Build the profile lookup in the shape odctl's planner expects."""
    return {
        profile: {"stack_id": stack_id, "file": stack.file}
        for stack_id, stack in registry.stacks.items()
        for profile in stack.profiles
    }


def _image(raw: str) -> str:
    return _TAG_PATTERN.sub(CLI_VERSION_TEXT, raw)


def _ports(service: dict) -> str:
    published = []
    for port in service.get("ports") or []:
        if isinstance(port, dict) and "published" in port:
            published.append(f"{port['published']}:{port.get('target', '')}")
        else:
            published.append(str(port))
    return ", ".join(f"`{p}`" for p in published) or "none"


def _memory(service: dict) -> str:
    limit = service.get("mem_limit")
    if limit is None:
        limit = (
            (service.get("deploy") or {})
            .get("resources", {})
            .get("limits", {})
            .get("memory")
        )
    return f"`{limit}`" if limit is not None else "not set"


def _services_table(compose: dict, profile: str) -> List[str]:
    rows = [
        "| Service | Image | Host:container ports | Memory limit |",
        "| --- | --- | --- | --- |",
    ]
    for name, service in (compose.get("services") or {}).items():
        if profile not in (service.get("profiles") or []):
            continue
        image = _image(str(service.get("image", "built locally")))
        rows.append(
            f"| `{name}` | `{image}` | {_ports(service)} | {_memory(service)} |"
        )
    return rows


def _usage(stack: StackConfig, profile: str) -> str:
    if isinstance(stack.usage, dict):
        return stack.usage.get(profile, "")
    return stack.usage or ""


# The areas the README uses, in the order the Profiles nav and the index show
# them. Each area is one page, with a section for each technology: its title and
# the profiles it covers, each profile a subsection. A technology with a lite and
# a full profile, such as Kafka, has a subsection for each. registry.yml has no
# such grouping, so it lives here, and a test fails when a profile is on no page
# or on two.
TECH_GROUPS: List[Tuple[str, List[Tuple[str, List[str]]]]] = [
    ("Messaging", [("Kafka", ["kafka-lite", "kafka-full"])]),
    (
        "Stream and batch processing",
        [
            ("Apache Flink", ["flink-lite", "flink-full"]),
            ("Apache Spark", ["spark-lite", "spark-full"]),
        ],
    ),
    (
        "Analytics",
        [
            ("ClickHouse", ["ch-lite", "ch-full"]),
            ("Trino", ["trino"]),
            ("Metabase", ["metabase"]),
        ],
    ),
    (
        "Orchestration",
        [
            ("Apache Airflow", ["airflow"]),
            ("Temporal", ["temporal"]),
        ],
    ),
    (
        "MLOps",
        [
            ("MLflow", ["mlflow"]),
            ("Feast", ["feast"]),
            ("Evidently", ["evidently"]),
        ],
    ),
    (
        "Metadata and lineage",
        [
            ("OpenMetadata", ["metadata"]),
            ("Marquez", ["lineage"]),
        ],
    ),
    ("Observability", [("Telemetry (grafana/otel-lgtm)", ["telemetry"])]),
    (
        "Storage and catalog",
        [
            ("PostgreSQL", ["postgres"]),
            ("SeaweedFS", ["storage"]),
            ("Iceberg REST catalog", ["catalog"]),
            ("Valkey", ["valkey"]),
            ("Apache Fluss", ["fluss"]),
            ("Shared dependencies", ["deps"]),
        ],
    ),
]


def _stack_of(registry: Registry, profile: str) -> Tuple[str, StackConfig]:
    for stack_id, stack in registry.stacks.items():
        if profile in stack.profiles:
            return stack_id, stack
    raise KeyError(f"profile {profile!r} is not in registry.yml")


def _slug(text: str) -> str:
    """The page name for an area, such as stream-and-batch-processing."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def tech_section(
    title: str,
    profiles: List[str],
    registry: Registry,
    resources: Path,
    profile_map: Dict[str, dict],
) -> List[str]:
    """Render one technology's section of an area page, a subsection per profile."""
    stack_id, stack = _stack_of(registry, profiles[0])
    compose = yaml.safe_load((resources / stack.file).read_text()) or {}
    lines = [
        f"## {title}",
        "",
        f"Profiles: {', '.join(f'`{p}`' for p in profiles)}. Stack `{stack_id}`, defined in `{stack.file}`.",
        "",
    ]
    for profile in profiles:
        direct = stack.depends_on.get(profile, [])
        started = sorted(
            resolve_dependencies([profile], profile_map, registry) - {profile}
        )
        lines += [
            f"### {profile}",
            "",
            f"Depends on: {', '.join(f'`{d}`' for d in direct) or 'nothing'}. "
            f"`odctl up {profile}` also starts: "
            f"{', '.join(f'`{d}`' for d in started) or 'nothing else'}.",
            "",
        ]
        usage = _usage(stack, profile).rstrip()
        if usage:
            lines += ["```text", usage, "```", ""]
        lines += _services_table(compose, profile) + [""]
    return lines


def profile_pages(resources: Path = INTERNAL_RESOURCES_DIR) -> Dict[str, str]:
    """
    Build the profile section: an index, one page per area and its nav file.

    The nav has one entry per area in TECH_GROUPS. Each area page has a section
    per technology, and each profile is a subsection, which the index links to.

    Returns:
        Dict[str, str]: Page content keyed by its path under the docs directory.
    """
    registry = load_registry(resources)
    profile_map = _profile_map(registry)
    pages: Dict[str, str] = {}

    index = [
        "# Profiles",
        "",
        "A profile is what `odctl up` starts. These pages are generated from `registry.yml` and the compose files when the site is built.",
        "",
    ]
    summary = ["- [Overview](index.md)"]
    for group, techs in TECH_GROUPS:
        path = f"{_slug(group)}.md"
        page = [f"# {group}", ""]
        index += [
            f"## [{group}]({path})",
            "",
            "| Profile | Technology | Description |",
            "| --- | --- | --- |",
        ]
        summary.append(f"- [{group}]({path})")
        for title, profiles in techs:
            page += tech_section(title, profiles, registry, resources, profile_map)
            for profile in profiles:
                _, stack = _stack_of(registry, profile)
                index.append(
                    f"| [`{profile}`]({path}#{profile}) | {title} | {stack.description} |"
                )
        index.append("")
        pages[f"profiles/{path}"] = "\n".join(page)

    pages["profiles/index.md"] = "\n".join(index)
    pages["profiles/SUMMARY.md"] = "\n".join(summary) + "\n"
    return pages


def _help_text(args: List[str]) -> str:
    """Capture `odctl <args>` as a user sees it, without colour codes."""
    from typer import rich_utils
    from typer.testing import CliRunner

    from odctl.main import app

    # The app callback calls logging.basicConfig(force=True), which would remove
    # the handlers of whatever process runs this, so put them back afterwards.
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    try:
        # GitHub Actions makes Typer force terminal output, which adds colour
        # codes, and the width otherwise follows the machine that builds.
        with mock.patch.multiple(rich_utils, FORCE_TERMINAL=False, MAX_WIDTH=80):
            result = CliRunner().invoke(app, args, prog_name="odctl")
    finally:
        root.handlers[:] = handlers
        root.setLevel(level)
    if result.exit_code != 0:
        raise RuntimeError(f"odctl {' '.join(args)} exited {result.exit_code}")
    return "\n".join(line.rstrip() for line in result.output.strip().splitlines())


def visible_commands() -> List[str]:
    """List the commands `odctl --help` shows, in the order it shows them."""
    from odctl.main import app

    return [
        command.name or command.callback.__name__  # type: ignore[union-attr]
        for command in app.registered_commands
        if not command.hidden
    ]


def cli_reference() -> str:
    """Render the CLI reference from `odctl --help` and each command's help."""
    lines = [
        "# CLI reference",
        "",
        "This page holds the output of `odctl --help` and of `odctl <command> --help`, captured when the site was built.",
        "",
        "## odctl",
        "",
        "```text",
        _help_text(["--help"]),
        "```",
        "",
    ]
    for name in visible_commands():
        lines += [
            f"## odctl {name}",
            "",
            "```text",
            _help_text([name, "--help"]),
            "```",
            "",
        ]
    return "\n".join(lines)


def _write_site_files() -> None:
    import mkdocs_gen_files

    from mkdocs.structure.files import InclusionLevel

    for path, content in profile_pages().items():
        with mkdocs_gen_files.open(path, "w") as f:
            f.write(content)

    # literate-nav reads SUMMARY.md for the nav. Excluded, it is not also built
    # as a page, listed in the sitemap or indexed for search.
    summary = mkdocs_gen_files.files.get_file_from_path("profiles/SUMMARY.md")
    summary.inclusion = InclusionLevel.EXCLUDED

    with mkdocs_gen_files.open("cli.md", "w") as f:
        f.write(cli_reference())

    # The README and the site share one diagram, kept where the README links it.
    with mkdocs_gen_files.open("assets/diagram.png", "wb") as f:
        f.write((REPO / "image" / "diagram.png").read_bytes())


# mkdocs-gen-files runs this file with runpy, which names it "<run_path>".
if __name__ == "<run_path>":
    _write_site_files()
