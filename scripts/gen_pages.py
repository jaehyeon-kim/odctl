"""
Generate the documentation pages that must match what odctl runs.

mkdocs-gen-files runs this file during every build. It writes one page per technology
in registry.yml, built from the registry and the compose files, a CLI
reference built from the `--help` output of each command, and a JSON Output page
built from the models of each `--json` document. None is kept in
the repository, so a change to the registry, a compose file or a command shows
up in the next build.

The page builders are plain functions so the tests can call them directly.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

import yaml
from pydantic import TypeAdapter

from odctl.config import INTERNAL_RESOURCES_DIR
from odctl.models import Info, ProfileDetails, ProfileInfo, PsReport
from odctl.planner import get_profile_map, resolve_dependencies
from odctl.registry import Registry, StackConfig, load_registry
from odctl.workspace import ENV_FILE

REPO = Path(__file__).resolve().parent.parent

# Compose resolves the images odctl builds with ${TAG:-latest}, and TAG is the
# CLI version once `odctl init` has run.
_TAG_PATTERN = re.compile(r"\$\{TAG(?::?-[^}]*)?\}")
CLI_VERSION_TEXT = "<CLI version>"


def _image(raw: str) -> str:
    return _TAG_PATTERN.sub(CLI_VERSION_TEXT, raw)


def _untagged(image: str) -> str:
    # The skill names images without their tag or digest, so a Renovate image
    # update does not change the committed SKILL.md and fail its test.
    image = image.split("@", 1)[0]
    repository, _, name = image.rpartition("/")
    name = name.split(":", 1)[0]
    return f"{repository}/{name}" if repository else name


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


def _services_table(compose: dict, profile: str, tags: bool = True) -> List[str]:
    rows = [
        "| Service | Image | Host:container ports | Memory limit |",
        "| --- | --- | --- | --- |",
    ]
    for name, service in (compose.get("services") or {}).items():
        if profile not in (service.get("profiles") or []):
            continue
        image = _image(str(service.get("image", "built locally")))
        if not tags:
            image = _untagged(image)
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
        "MLflow, Feast, Evidently, Label Studio",
        [
            ("MLflow", ["mlflow"]),
            ("Feast", ["feast"]),
            ("Evidently", ["evidently"]),
            ("Label Studio", ["label-studio"]),
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
    (
        "AI Engineering",
        "Langfuse",
        [("Langfuse", ["langfuse"])],
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
    registry = load_registry(resources / "registry.yml")
    profile_map = get_profile_map(registry)
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


# Each command with `--json`, what it prints and the type of that document.
JSON_OUTPUTS: List[Tuple[str, str, Any]] = [
    (
        "list",
        "an array with one object for each profile, sorted by profile name",
        List[ProfileInfo],
    ),
    ("explain", "one object for the profile you name", ProfileDetails),
    (
        "ps",
        "one object with the active profiles and the matching containers",
        PsReport,
    ),
    (
        "info",
        "one object with the CLI version, the image tag, the workspace, Docker and odctl's own images",
        Info,
    ),
]


def json_output_page() -> str:
    """
    Render the JSON Output page from the models of each `--json` document.

    The schemas come from `model_json_schema(mode="serialization")`, so a field
    the model leaves out of its JSON is not on the page. Each schema keeps the
    description of its fields and drops the docstring of its model, which is
    written for the code's readers.

    Returns:
        str: The Markdown of the JSON Output page.
    """
    lines = [
        "# JSON Output",
        "",
        "`odctl list`, `odctl explain`, `odctl ps` and `odctl info` print one JSON document with `--json`, for scripts and AI assistants. The `list`, `explain`, `ps` and `info` tools of the [MCP server](guides/mcp-server.md) return the same documents. This page holds the JSON Schema of each document, captured when the site was built. A JSON Schema lists the keys of a document, the type of each value and which keys are always present. Standard output holds only the JSON document. Warnings and errors go to standard error. A usage error, such as an unknown option, exits with code 2. Any other failure exits with code 1 and prints nothing on standard output. [What Stays Stable in 1.x](how-it-works.md#what-stays-stable-in-1x) says which changes to these keys wait for 2.0.",
        "",
    ]
    for command, shape, model in JSON_OUTPUTS:
        schema = TypeAdapter(model).json_schema(mode="serialization")
        for described in [schema, *schema.get("$defs", {}).values()]:
            described.pop("description", None)
        lines += [
            f"## odctl {command}",
            "",
            f"`odctl {command} --json` prints {shape}. Its schema:",
            "",
            "```json",
            json.dumps(schema, indent=2),
            "```",
            "",
        ]
    return "\n".join(lines)


SKILL_DIR = REPO / "skills" / "odctl"


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
    "AIRFLOW_OPENLINEAGE_TRANSPORT": 'Where Airflow sends OpenLineage events, as JSON such as `{"type": "http", "url": "http://marquez-api:5000"}`; empty means Airflow sends none.',
    "_METADATA_PIP_DEPS": "Extra Python packages installed in every new `openmetadata-ingestion` container.",
    "METADATA_AUTOPILOT": "`true` turns on OpenMetadata's AutoPilot, which creates and runs default agents for a service added in the UI; it is `false` by default.",
    "MODEL_URI": "The model `mlflow-serve` serves, such as `models:/<name>@<alias>`; empty means it waits idle.",
}


def env_keys() -> List[str]:
    """
    List the keys `odctl init` writes to `.odctl/.env`, in the order it writes them.

    Returns:
        List[str]: The key names, from `workspace.ENV_FILE`.
    """
    return [key for group in ENV_FILE for _, key, _ in group]


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


# The skill's hand-written files: SKILL.md, with this marker where the generated
# tables go, and the pages under references/, copied as they are.
SKILL_SOURCE = REPO / "scripts" / "skill"
TABLES_MARKER = "<!-- commands, options and workspace settings, generated by scripts/gen_pages.py -->"

# The services whose images declare data volumes, which `odctl recreate` passes on
# to the new container (How It Works, Where Data Lives). The generator fails when one
# is no longer a service, so a rename reaches this list.
KEEPS_DATA_ON_RECREATE = {
    "postgres",
    "seaweed",
    "ch-keeper",
    "ch-11",
    "ch-11-full",
    "ch-12",
    "ch-12-full",
    "ch-21",
    "ch-22",
    "fluss-zookeeper",
}

# The services that keep their data in a database of the postgres profile, from
# their compose environment or the config file they mount, so a down or recreate of
# their own profile keeps it while postgres runs. The generator fails when one is no
# longer a service, so a rename reaches this list.
POSTGRES_DATABASES = {
    "airflow": "airflow",
    "metabase": "metabase",
    "marquez-api": "marquez",
    "catalog": "iceberg",
    "mlflow": "mlflow",
    "feast-ui": "feast",
    "feast-serve": "feast",
    "evidently": "evidently",
    "label-studio": "labelstudio",
    "openmetadata-migrate": "omt",
    "openmetadata-server": "omt",
    "openmetadata-ingestion": "omt",
    "langfuse-web": "langfuse",
    "langfuse-worker": "langfuse",
}

# What a profile's notes leave out and a client needs: a login that is not the
# usual user and password, or where a client writes.
PROFILE_NOTES = {
    "ch-lite": "Login: the user `default` with the password `password`, from the host and from a container (`CLICKHOUSE_PASSWORD` in `compose-analytics.yml`). A request with no password fails with `AUTHENTICATION_FAILED`.",
    "ch-full": "Login: the user `default` with the password `password`, from the host and from a container (`CLICKHOUSE_PASSWORD` in `compose-analytics.yml`). A request with no password fails with `AUTHENTICATION_FAILED`.",
    "airflow": 'DAGs: a new DAG starts paused (`AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION` in `compose-orch.yml`), and a run triggered on a paused DAG stays queued. After an upload, wait with a limit until Airflow lists the DAG, then unpause it (`airflow dags unpause <dag_id>`, or `PATCH /api/v2/dags/<dag_id>` with `{"is_paused": false}`) and trigger it. Unpausing a DAG that has a schedule also starts a scheduled run. On a stack where the DAG was uploaded before, Airflow lists the stored DAG before it parses the new file.',
    "metadata": "Agents: after `POST /api/v1/services/ingestionPipelines/deploy/<id>`, the ingestion Airflow parses the new DAG before `POST .../trigger/<id>` works, so repeat the trigger every 5 seconds, with a limit, until it answers that the workflow has been triggered.",
    "fluss": "Readiness: `fluss-tablet-1` registers in ZooKeeper a few seconds after it starts, and a `CREATE TABLE` before then fails. Wait, with a limit, until `docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids` prints a list that holds `0`.",
    "langfuse": "Events: `langfuse-web` stores each event in the `langfuse` bucket of `seaweed` (`storage`) and queues it in `valkey`, and `langfuse-worker` writes it to the `langfuse` database of ClickHouse on `ch-11` (`ch-lite`) (`compose-aieng.yml`). `odctl down langfuse` and `odctl recreate langfuse` keep them while those profiles run; `odctl down storage`, `odctl down valkey` and `odctl down ch-lite` lose that part.",
    "feast": "Registry: the bundled `feature_store.yaml` keeps Feast's SQL registry in the `feast` database of `postgres`: `postgresql+psycopg://user:password@postgres:5432/feast` from a container, and `127.0.0.1:5432` from the host. The online store is `valkey`.",
}

# What each named volume holds. A profile's volume without a line here fails the
# skill build. odctl-shared-deps is described only under deps, which fills it.
VOLUME_NOTES = {
    "odctl-shared-deps": "The named volume `odctl-shared-deps` holds only the jars `init-deps` copies, so `odctl down --volumes` removes it only once no other profile has a container.",
    "spark-events-data": "The named volume `spark-events-data` holds Spark's event logs in memory, so it holds nothing once the stack is down.",
}

# Settings a profile's service reads only when it creates its data, so a recreate,
# which keeps that data, does not apply them.
FIRST_CREATION_NOTES = {
    "postgres": "`TZ` and `postgres/01-init-databases.sh`, which creates each service's database, take effect only when PostgreSQL creates its data folder. A recreate keeps that folder, so they change after `odctl down postgres` and `odctl up postgres`.",
}


# The services that do one job and exit, such as copying jars or creating buckets.
# `odctl up` waits for them to finish, so the Health line leaves them out. The
# generator fails when one is no longer a service, so a rename reaches this list.
ONE_SHOT_SERVICES = {
    "init-deps",
    "seaweed-init",
    "openmetadata-migrate",
    "openmetadata-init",
}


def _joined(names: List[str]) -> str:
    """Names joined as a sentence lists them: "a", "a and b", "a, b and c"."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _health_test(service: dict) -> Optional[str]:
    """The command of a service's health check as a shell would run it, or None."""
    check = service.get("healthcheck") or {}
    test = check.get("test")
    if not test or check.get("disable"):
        return None
    if isinstance(test, list):
        test = " ".join(test[1:]) if test[0] in ("CMD", "CMD-SHELL") else " ".join(test)
    # Why: Compose reads `$$` as a literal `$`, which is what the container runs
    return test.replace("$$", "$").removesuffix(" || exit 1")


def _health_lines(compose: dict, profile: str) -> List[str]:
    """Which services `odctl up` and `odctl recreate` wait for, and with what check."""
    checked = []
    unchecked = []
    for name, service in (compose.get("services") or {}).items():
        if profile not in (service.get("profiles") or []) or name in ONE_SHOT_SERVICES:
            continue
        test = _health_test(service)
        if test:
            checked.append(f"`{name}` (`{test}`)")
        else:
            unchecked.append(f"`{name}`")
    text = []
    if checked:
        text.append(
            f"`odctl up` and `odctl recreate` return once {_joined(checked)} "
            f"{'passes its health check' if len(checked) == 1 else 'pass their health checks'}, "
            "so call what the check tests with no wait loop."
        )
    if unchecked:
        text.append(
            f"{_joined(unchecked)} {'has' if len(unchecked) == 1 else 'have'} no health check: "
            "the commands return once "
            f"{'it runs' if len(unchecked) == 1 else 'they run'}, "
            "so wait for what the task needs from "
            f"{'it' if len(unchecked) == 1 else 'them'}, with a limit."
        )
    return [f"Health: {' '.join(text)}"] if text else []


def _data_lines(compose: dict, profile: str) -> List[str]:
    """Where a profile's services keep their data, and what recreate and down do to it."""
    services = [
        (name, service)
        for name, service in (compose.get("services") or {}).items()
        if profile in (service.get("profiles") or [])
    ]
    kept = [name for name, _ in services if name in KEEPS_DATA_ON_RECREATE]
    in_postgres = [name for name, _ in services if name in POSTGRES_DATABASES]
    if in_postgres:
        databases = sorted({POSTGRES_DATABASES[n] for n in in_postgres})
        text = (
            f"{_joined([f'`{n}`' for n in in_postgres])} "
            f"{'keeps its' if len(in_postgres) == 1 else 'keep their'} data in the "
            f"{_joined([f'`{d}`' for d in databases])} "
            f"{'database' if len(databases) == 1 else 'databases'} of the `postgres` profile, "
        )
        if "postgres" in (compose.get("services") or {}):
            # Why: down and recreate also act on the profiles of the same compose
            # file that this one depends on (planner.expand_plan_dependencies)
            text += (
                "which shares its compose file, so `odctl down "
                f"{profile}` also stops `postgres` and loses it, "
                f"and `odctl recreate {profile}` also recreates `postgres`, which keeps it. "
            )
        else:
            text += (
                f"so `odctl down {profile}` and `odctl recreate {profile}` keep it while `postgres` runs, "
                "and `odctl down postgres` loses it. "
            )
        text += (
            "The other services keep their data inside their containers."
            if len(in_postgres) < len(services)
            else ""
        )
    elif kept:
        text = (
            f"{_joined([f'`{n}`' for n in kept])} "
            f"{'keeps its data in unnamed volumes that its image declares' if len(kept) == 1 else 'keep their data in unnamed volumes that their images declare'}: "
            "`odctl recreate` keeps it, "
            "and `odctl down` loses it. "
        )
        text += (
            "The other services keep their data inside their containers."
            if len(kept) < len(services)
            else ""
        )
    else:
        text = "Every service keeps its data inside its container, so `odctl recreate` and `odctl down` lose it, and `odctl restart` keeps it."
    volumes = (compose.get("volumes") or {}).keys()
    mounted: List[str] = []
    for _, service in services:
        for mount in service.get("volumes") or []:
            source = str(
                mount.get("source") if isinstance(mount, dict) else mount.split(":")[0]
            )
            if source in volumes and source not in mounted:
                mounted.append(source)
    if profile != "deps" and "odctl-shared-deps" in mounted:
        mounted.remove("odctl-shared-deps")
    notes = [text.strip()] + [VOLUME_NOTES[v] for v in mounted]
    if profile in FIRST_CREATION_NOTES:
        notes.append(FIRST_CREATION_NOTES[profile])
    return [f"Data: {' '.join(notes)}"]


def skill() -> str:
    """
    Render the odctl skill's SKILL.md from its source and the CLI.

    Returns:
        str: scripts/skill/SKILL.md with the Commands, Options and Workspace
        Settings tables in place of its marker.

    Raises:
        ValueError: When the source has no marker.
    """
    template = (SKILL_SOURCE / "SKILL.md").read_text()
    if TABLES_MARKER not in template:
        raise ValueError(f"scripts/skill/SKILL.md has no {TABLES_MARKER!r}")
    tables = "\n".join(_command_tables()).rstrip()
    return template.replace(TABLES_MARKER, tables)


def profiles_reference(resources: Path = INTERNAL_RESOURCES_DIR) -> str:
    """
    Render the skill's references/profiles.md from the registry and the compose files.

    Args:
        resources (Path): The folder that holds registry.yml and the compose files.

    Returns:
        str: The Markdown page, with a contents list and a section per profile.

    Raises:
        ValueError: When a service of KEEPS_DATA_ON_RECREATE, POSTGRES_DATABASES or
            ONE_SHOT_SERVICES is in no compose file.
    """
    registry = load_registry(resources / "registry.yml")
    profile_map = get_profile_map(registry)
    contents = []
    sections: List[str] = []
    services = set()
    for group, _, techs in TECH_GROUPS:
        group_profiles = []
        sections += [f"## {group}", ""]
        for title, profiles in techs:
            _, stack = _stack_of(registry, profiles[0])
            compose = yaml.safe_load((resources / stack.file).read_text()) or {}
            services |= set((compose.get("services") or {}).keys())
            for profile in profiles:
                group_profiles.append(f"[{profile}](#{profile})")
                started = sorted(
                    resolve_dependencies([profile], profile_map, registry) - {profile}
                )
                sections += [
                    f"### {profile}",
                    "",
                    f"{title}: {stack.description} `odctl up {profile}` also starts: {', '.join(f'`{d}`' for d in started) or 'nothing else'}.",
                    "",
                ]
                usage = _usage(stack, profile).rstrip()
                if usage:
                    sections += ["```text", usage, "```", ""]
                sections += _services_table(compose, profile, tags=False) + [""]
                sections += _health_lines(compose, profile) + [""]
                if profile in PROFILE_NOTES:
                    sections += [PROFILE_NOTES[profile], ""]
                sections += _data_lines(compose, profile) + [""]
        contents.append(f"- {group}: {', '.join(group_profiles)}")
    missing = sorted(
        (KEEPS_DATA_ON_RECREATE | set(POSTGRES_DATABASES) | ONE_SHOT_SERVICES)
        - services
    )
    if missing:
        raise ValueError(
            "KEEPS_DATA_ON_RECREATE, POSTGRES_DATABASES or ONE_SHOT_SERVICES "
            f"names no service: {missing}"
        )
    lines = [
        "# odctl Profiles",
        "",
        "Each section gives a profile's addresses from the host and from a container, its logins, what `odctl up` also starts, its services with their images, ports and memory limits, which services `odctl up` waits for, and where its data lives. Every port is published on `127.0.0.1` only. This page is generated from odctl's `registry.yml` and compose files.",
        "",
        "## Contents",
        "",
        *contents,
        "",
        *sections,
    ]
    return "\n".join(lines).rstrip() + "\n"


def skill_files(resources: Path = INTERNAL_RESOURCES_DIR) -> Dict[str, str]:
    """
    Render every file of the skill folder skills/odctl/.

    A test fails when the committed folder differs from this output, so a new
    profile, port, command or edit of a source under scripts/skill/ reaches it.

    Args:
        resources (Path): The folder that holds registry.yml and the compose files.

    Returns:
        Dict[str, str]: Each file's path inside the folder and its content.
    """
    files = {
        "SKILL.md": skill(),
        "references/profiles.md": profiles_reference(resources),
    }
    for page in sorted((SKILL_SOURCE / "references").glob("*.md")):
        files[f"references/{page.name}"] = page.read_text()
    return files


PLUGIN_NAME = "odctl"
PLUGIN_DESCRIPTION = (
    "Adds the odctl agent skill and a read-only MCP server, which need odctl "
    "installed: uv tool install 'odctl[mcp]'."
)
PLUGIN_REPOSITORY = "https://github.com/jaehyeon-kim/odctl"
PLUGIN_LOGO = "./docs/assets/logo.png"
PLUGIN_AUTHOR = "Jaehyeon Kim"

# The one MCP server entry. It has no --allow-changes, so `up` and `down` are not
# served. Claude Code and Codex read it inline from their plugin.json, because a
# root .mcp.json is also the repository's own project MCP file, which every
# Claude Code session in odctl would load. Antigravity reads it from its own file
# at the plugin root.
PLUGIN_MCP = {"mcpServers": {"odctl": {"command": "odctl", "args": ["mcp"]}}}
PLUGIN_MCP_FILES = ("mcp_config.json",)


def package_version() -> str:
    """
    Read the version from pyproject.toml.

    The text is read, not parsed with tomllib, which Python 3.10 lacks.

    Returns:
        str: The package version.

    Raises:
        ValueError: When pyproject.toml has no `version` line in [project].
    """
    text = (REPO / "pyproject.toml").read_text()
    # Why: the match stops at the next table header, so a later table's version
    # is never read as the package's
    match = re.search(
        r'^\[project\]\n(?:(?!^\[).*\n)*?^version = "([^"]+)"', text, re.M
    )
    if not match:
        raise ValueError("pyproject.toml has no version in [project]")
    return match.group(1)


def plugin_files(version: Optional[str] = None) -> Dict[str, str]:
    """
    Render the plugin manifests and MCP files for Claude Code, Codex and Antigravity.

    All sit at the repository root, which each tool copies on install. A test
    fails when a committed file differs from this output, so every manifest
    carries the version of pyproject.toml.

    Args:
        version (Optional[str]): The version to write. Defaults to pyproject.toml's.

    Returns:
        Dict[str, str]: Each file's path from the repository root and its content.

    Raises:
        ValueError: When no version is given and pyproject.toml has none in [project].
    """
    version = version or package_version()
    base: Dict[str, Any] = {
        "name": PLUGIN_NAME,
        "version": version,
        "description": PLUGIN_DESCRIPTION,
        "author": {"name": PLUGIN_AUTHOR},
        "homepage": PLUGIN_REPOSITORY,
        "repository": PLUGIN_REPOSITORY,
        "license": "Apache-2.0",
        "keywords": ["data-stack", "docker-compose", "mcp", "skill"],
    }
    marketplace: Dict[str, Any] = {
        "name": PLUGIN_NAME,
        "description": PLUGIN_DESCRIPTION,
        "owner": {"name": PLUGIN_AUTHOR},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": "./",
                "description": PLUGIN_DESCRIPTION,
            }
        ],
    }
    claude = {**base, "icon": PLUGIN_LOGO.removeprefix("./"), **PLUGIN_MCP}
    codex = {
        **base,
        **PLUGIN_MCP,
        "interface": {
            "displayName": PLUGIN_NAME,
            "shortDescription": "Run an open data stack from one command",
            "category": "Coding",
            "logo": PLUGIN_LOGO,
        },
    }
    antigravity = {
        "name": PLUGIN_NAME,
        "version": version,
        "description": PLUGIN_DESCRIPTION,
        "logo": PLUGIN_LOGO.removeprefix("./"),
    }
    documents: Dict[str, Any] = {
        ".claude-plugin/plugin.json": claude,
        ".claude-plugin/marketplace.json": marketplace,
        ".codex-plugin/plugin.json": codex,
        ".agents/plugins/marketplace.json": {
            "name": PLUGIN_NAME,
            "plugins": [{"name": PLUGIN_NAME, "source": "./"}],
        },
        ".antigravity-plugin/plugin.json": antigravity,
        **{name: PLUGIN_MCP for name in PLUGIN_MCP_FILES},
    }
    return {
        path: json.dumps(document, indent=2) + "\n"
        for path, document in documents.items()
    }


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

    with mkdocs_gen_files.open("json-output.md", "w") as f:
        f.write(json_output_page())

    # The README and the site share one diagram and one recording, kept where
    # the README links them.
    for name in ("diagram.png", "demo.gif"):
        with mkdocs_gen_files.open(f"assets/{name}", "wb") as f:
            f.write((REPO / "image" / name).read_bytes())


# mkdocs-gen-files runs this file with runpy, which names it "<run_path>".
if __name__ == "<run_path>":
    _write_site_files()

# `uv run python scripts/gen_pages.py` writes the skill folder and the plugin files.
if __name__ == "__main__":
    written = skill_files()
    for stale in SKILL_DIR.rglob("*"):
        if stale.is_file() and stale.relative_to(SKILL_DIR).as_posix() not in written:
            stale.unlink()
            print(f"removed {stale.relative_to(REPO)}")
    for name, content in written.items():
        path = SKILL_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"wrote {path.relative_to(REPO)}")
    for name, content in plugin_files().items():
        path = REPO / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"wrote {name}")
