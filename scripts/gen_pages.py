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
    """
    Read registry.yml from a resources directory into odctl's own model.

    Args:
        resources (Path): The folder that holds registry.yml.

    Returns:
        Registry: The parsed registry.
    """
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
            # Every port binds to 127.0.0.1, which the page says once.
            published.append(str(port).removeprefix("127.0.0.1:"))
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


# The single list of areas for the docs: the Profiles nav, the area pages and
# the home page's "What it runs" table all come from here, in this order. Each
# entry is an area, the technologies that table lists for it, and its
# technologies with their profiles. Each area is one page, with a section for each technology: its title and
# the profiles it covers, each profile a subsection. A technology with a lite and
# a full profile, such as Kafka, has a subsection for each. registry.yml has no
# such grouping, so it lives here, and a test fails when a profile is on no page
# or on two.
TECH_GROUPS: List[Tuple[str, str, List[Tuple[str, List[str]]]]] = [
    (
        "Messaging",
        "Kafka (KRaft), Karapace schema registry, Kafka Connect, Kafka UI (kafbat)",
        [("Kafka", ["kafka-lite", "kafka-full"])],
    ),
    (
        "Stream and Batch Processing",
        "Apache Flink, Apache Spark",
        [
            ("Apache Flink", ["flink-lite", "flink-full"]),
            ("Apache Spark", ["spark-lite", "spark-full"]),
        ],
    ),
    (
        "Analytics",
        "ClickHouse, Trino, Metabase",
        [
            ("ClickHouse", ["ch-lite", "ch-full"]),
            ("Trino", ["trino"]),
            ("Metabase", ["metabase"]),
        ],
    ),
    (
        "Orchestration",
        "Apache Airflow, Temporal",
        [
            ("Apache Airflow", ["airflow"]),
            ("Temporal", ["temporal"]),
        ],
    ),
    (
        "MLOps",
        "MLflow, Feast, Evidently",
        [
            ("MLflow", ["mlflow"]),
            ("Feast", ["feast"]),
            ("Evidently", ["evidently"]),
        ],
    ),
    (
        "Metadata and Lineage",
        "OpenMetadata, Marquez",
        [
            ("OpenMetadata", ["metadata"]),
            ("Marquez", ["lineage"]),
        ],
    ),
    (
        "Observability",
        "grafana/otel-lgtm (OpenTelemetry Collector, Prometheus, Tempo, Loki, Grafana)",
        [("Telemetry (grafana/otel-lgtm)", ["telemetry"])],
    ),
    (
        "Storage and Catalog",
        "PostgreSQL 18 with pgvector, pg_textsearch and PostGIS, SeaweedFS (S3), Iceberg REST catalog, Valkey Bundle, Apache Fluss",
        [
            ("PostgreSQL", ["postgres"]),
            ("SeaweedFS", ["storage"]),
            ("Iceberg REST Catalog", ["catalog"]),
            ("Valkey", ["valkey"]),
            ("Apache Fluss", ["fluss"]),
            ("Shared Dependencies", ["deps"]),
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


def _tech_section(
    title: str,
    profiles: List[str],
    registry: Registry,
    resources: Path,
    profile_map: Dict[str, dict],
) -> List[str]:
    """
    Render one technology's section of an area page, a subsection per profile.

    Args:
        title (str): The technology's heading.
        profiles (List[str]): Its profiles, all from one compose file.
        registry (Registry): The parsed registry.
        resources (Path): The folder that holds the compose files.
        profile_map (Dict[str, dict]): The stack and compose file of each profile.

    Returns:
        List[str]: The section's Markdown lines.
    """
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

    Args:
        resources (Path): The folder that holds registry.yml and the compose files.

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
    for group, _, techs in TECH_GROUPS:
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
            page += _tech_section(title, profiles, registry, resources, profile_map)
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
    """
    List the commands `odctl --help` shows, in the order it shows them.

    Returns:
        List[str]: The names of the commands that are not hidden.
    """
    from odctl.main import app

    return [
        command.name or command.callback.__name__  # type: ignore[union-attr]
        for command in app.registered_commands
        if not command.hidden
    ]


def cli_reference() -> str:
    """
    Render the CLI reference from `odctl --help` and each command's help.

    Returns:
        str: The Markdown of the CLI reference page.
    """
    lines = [
        "# CLI Reference",
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


SKILL_PATH = REPO / "skills" / "odctl" / "SKILL.md"


def _command_summaries() -> List[Tuple[str, str]]:
    """Each visible command with the first line of its help."""
    from odctl.main import app

    rows = []
    for command in app.registered_commands:
        if command.hidden:
            continue
        name = command.name or command.callback.__name__  # type: ignore[union-attr]
        doc = (command.help or command.callback.__doc__ or "").strip()  # type: ignore[union-attr]
        rows.append((name, doc.splitlines()[0] if doc else ""))
    return rows


def _options(callback) -> List[Tuple[str, str]]:
    """The flags and help text of each Typer option of one command function."""
    import inspect

    import typer

    found = []
    for param in inspect.signature(callback).parameters.values():
        info = param.default
        if isinstance(info, typer.models.OptionInfo):
            decls = list(info.param_decls or [])
            if isinstance(info.default, str) and info.default.startswith("-"):
                decls.insert(0, info.default)
            found.append((", ".join(decls), (info.help or "").strip()))
    return found


def command_options() -> List[Tuple[str, str, str]]:
    """
    Each option of each visible command, and the global options, from the Typer app.

    Returns:
        List[Tuple[str, str, str]]: The command (empty for a global option), the
        option's flags joined with ", " such as "--all, -a", and its help text.
    """
    from odctl.main import app

    rows: List[Tuple[str, str, str]] = []
    if app.registered_callback is not None and app.registered_callback.callback:
        rows += [("", f, h) for f, h in _options(app.registered_callback.callback)]
    for command in app.registered_commands:
        if command.hidden:
            continue
        name = command.name or command.callback.__name__  # type: ignore[union-attr]
        rows += [(name, f, h) for f, h in _options(command.callback)]
    return rows


# What each `.env` key that `odctl init` writes is for. env_keys() reads the keys
# from odctl/workspace.py, so a new key without a line here fails the skill build.
ENV_KEYS = {
    "TAG": "The tag of odctl's own images, set to the CLI version. A `TAG` in the shell overrides it.",
    "TZ": "The time zone of the services that read it, `UTC` by default.",
    "_AIRFLOW_PIP_DEPS": "Extra Python packages installed in every new Airflow container.",
    "_MLOPS_PIP_DEPS": "Extra Python packages installed in every new `mlflow` and `mlflow-serve` container.",
    "MODEL_URI": "The model `mlflow-serve` serves, such as `models:/<name>@<alias>`; empty means it waits idle.",
}


def env_keys() -> List[str]:
    """
    List the keys `odctl init` writes to `.odctl/.env`, in the order it writes them.

    Returns:
        List[str]: The key names, read from `workspace.py`.
    """
    source = (REPO / "src" / "odctl" / "workspace.py").read_text()
    return re.findall(r"""f\.write\(f?["']([A-Z_]+)=""", source)


def _command_tables() -> List[str]:
    """The skill's Commands, Options and Workspace Settings tables, read from the CLI."""
    lines = [
        "## Commands",
        "",
        "| Command | Does |",
        "| --- | --- |",
    ]
    lines += [f"| `odctl {name}` | {doc} |" for name, doc in _command_summaries()]
    lines += [
        "",
        "## Options",
        "",
        "Global options go before the command, as in `odctl --workspace ../shared/.odctl ps --all`.",
        "",
        "| Command | Option | Does |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {f'`odctl {name}`' if name else 'global'} | `{flags}` | {text} |"
        for name, flags, text in command_options()
    ]
    lines += [
        "",
        "## Workspace Settings",
        "",
        "`odctl init` writes these keys to `.odctl/.env`. Run `odctl recreate <profile>` after changing one.",
        "",
        "| Key | Sets |",
        "| --- | --- |",
    ]
    lines += [f"| `{key}` | {ENV_KEYS[key]} |" for key in env_keys()]
    lines.append("")
    return lines


def skill(resources: Path = INTERNAL_RESOURCES_DIR) -> str:
    """
    Render the odctl skill for AI assistants from the registry and the compose files.

    It is committed at skills/odctl/SKILL.md, and a test fails when the file
    differs from this output, so a new profile, port or command reaches it.

    Args:
        resources (Path): The folder that holds registry.yml and the compose files.

    Returns:
        str: The skill's Markdown.
    """
    registry = load_registry(resources)
    profile_map = _profile_map(registry)
    lines = [
        "---",
        "name: odctl",
        "description: Start a local open data stack with odctl and reach its services. Use when a task needs Kafka, Flink, Spark, Iceberg, Trino, ClickHouse, PostgreSQL, SeaweedFS, MLflow, Feast, Evidently, Airflow, Temporal, Marquez, OpenMetadata, Valkey, Fluss or Grafana running locally in Docker.",
        "---",
        "",
        "# odctl",
        "",
        "odctl starts open source data services as Docker Compose profiles. Install it with `uv tool install odctl` or `pipx install odctl`; it needs Docker. This file is generated from odctl's `registry.yml` and compose files.",
        "",
        "## How to Use It",
        "",
        "- Start what the task needs with `odctl up <profile> [<profile> ...]`. Each profile also starts the profiles it depends on, listed below, and `odctl up` returns once every service is running, and healthy where it has a health check.",
        "- `odctl up <profile> --dry-run` prints the plan without starting anything. `odctl explain <profile>` shows its services, images and dependencies.",
        "- `odctl down <profile>` stops only the profiles named, not their dependencies. Services keep their data inside their containers, so `down` deletes it. Add `--volumes` to also remove named volumes: the shared jar volume `odctl-shared-deps` and Spark's `spark-events-data`. `odctl down --all --volumes` removes everything.",
        "- Every port is published on `127.0.0.1` only, so other machines cannot reach it. From the host, use `127.0.0.1` and the host port. From a container, join the `odctl` Docker network and use the container name and container port, for example `broker-1:19092` or `http://catalog:8181`.",
        "- Logins are in each profile's notes below. Most services use the user `user` and the password `password`; some have no login.",
        "- `odctl init` copies the compose files, `registry.yml` and `.env` into `.odctl/` in the current directory, so they can be edited. Run `odctl recreate <profile>` after editing a compose file or `.env`.",
        "- `-lite` profiles run one node of a tool; `-full` profiles run a cluster of it. Start one of the pair, not both.",
        "",
    ]
    lines += _command_tables()
    for group, _, techs in TECH_GROUPS:
        lines += [f"## {group}", ""]
        for title, profiles in techs:
            _, stack = _stack_of(registry, profiles[0])
            compose = yaml.safe_load((resources / stack.file).read_text()) or {}
            for profile in profiles:
                started = sorted(
                    resolve_dependencies([profile], profile_map, registry) - {profile}
                )
                lines += [
                    f"### {profile}",
                    "",
                    f"{title}: {stack.description} `odctl up {profile}` also starts: {', '.join(f'`{d}`' for d in started) or 'nothing else'}.",
                    "",
                ]
                usage = _usage(stack, profile).rstrip()
                if usage:
                    lines += ["```text", usage, "```", ""]
                lines += _services_table(compose, profile) + [""]
    return "\n".join(lines).rstrip() + "\n"


# The home page holds this marker where the "What it runs" table goes.
AREAS_MARKER = "<!-- areas table, generated by scripts/gen_pages.py -->"


def areas_table() -> str:
    """
    Render the home page table of each area and the technologies it runs.

    Returns:
        str: The Markdown table.
    """
    lines = ["| Area | Technologies |", "| --- | --- |"]
    for group, summary, _ in TECH_GROUPS:
        lines.append(f"| [{group}](profiles/{_slug(group)}.md) | {summary} |")
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

    with mkdocs_gen_files.open("index.md", "r") as f:
        home = f.read()
    if AREAS_MARKER not in home:
        raise ValueError(f"docs/index.md has no {AREAS_MARKER!r}")
    with mkdocs_gen_files.open("index.md", "w") as f:
        f.write(home.replace(AREAS_MARKER, areas_table()))

    with mkdocs_gen_files.open("cli.md", "w") as f:
        f.write(cli_reference())

    # The README and the site share one diagram and one recording, kept where
    # the README links them.
    for name in ("diagram.png", "demo.gif"):
        with mkdocs_gen_files.open(f"assets/{name}", "wb") as f:
            f.write((REPO / "image" / name).read_bytes())


# mkdocs-gen-files runs this file with runpy, which names it "<run_path>".
if __name__ == "<run_path>":
    _write_site_files()

# `uv run python scripts/gen_pages.py` writes the skill.
if __name__ == "__main__":
    SKILL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SKILL_PATH.write_text(skill())
    print(f"wrote {SKILL_PATH.relative_to(REPO)}")
