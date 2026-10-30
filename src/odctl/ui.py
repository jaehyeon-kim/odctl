from typing import Dict, List, Optional

import typer
from pydantic import BaseModel, TypeAdapter
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from odctl.models import Info, ProfileDetails, ProfileInfo, PsReport

console = Console()
_error_console = Console(stderr=True)

_json_output = False


def set_json_output(enabled: bool) -> None:
    """
    Choose where warnings and errors go.

    With JSON output, stdout holds one JSON document, so `print_error` and `print_info`
    write to stderr. Without it, they write to stdout.

    Args:
        enabled (bool): True when the command was given `--json`.
    """
    global _json_output
    _json_output = enabled


def _message_console() -> Console:
    """
    Return the console that warnings and errors print to.

    Returns:
        Console: The stderr console under `--json`, otherwise the stdout console.
    """
    return _error_console if _json_output else console


def print_json(output: BaseModel | List[ProfileInfo]) -> None:
    """
    Print a model, or the list of profiles, as one JSON document on stdout.

    Args:
        output (BaseModel | List[ProfileInfo]): The model or the profiles to print.
    """
    if isinstance(output, BaseModel):
        typer.echo(output.model_dump_json())
    else:
        typer.echo(TypeAdapter(List[ProfileInfo]).dump_json(output).decode())


def print_profile_table(profiles: List[ProfileInfo], details: bool):
    """
    Format and print the list of available profiles to the console.

    Args:
        profiles (List[ProfileInfo]): The profiles in registry order. The profiles of one
            registry stack are one group: only the first row of a group shows the stack
            and description.
        details (bool): If True, also shows each profile's services and published ports,
            which need `ProfileInfo.services` to be filled.
    """
    table = Table(header_style="bold")
    table.add_column("Profile", style="green", no_wrap=True, vertical="middle")
    table.add_column("Parent Stack", style="cyan", vertical="middle")
    table.add_column("Description", max_width=60, vertical="middle")

    if details:
        table.add_column("Services", style="magenta", max_width=45, vertical="middle")
        table.add_column("Port Mappings", style="blue", max_width=55, vertical="middle")

    previous_stack_id = None
    for info in profiles:
        starts_group = info.stack_id != previous_stack_id
        if starts_group and previous_stack_id is not None:
            table.add_section()
        previous_stack_id = info.stack_id

        row = [
            info.profile,
            info.stack if starts_group else "",
            info.description if starts_group else "",
        ]

        if details:
            services = [s.name for s in info.services]
            row.append(", ".join(services) if services else "N/A")
            row.append(", ".join(info.port_specs) if info.port_specs else "N/A")

        table.add_row(*row)

    if profiles:
        table.add_section()
    console.print(table)


# Printed under every `odctl explain`. With IPv6 enabled on the Docker network,
# localhost reaches the container's IPv6 address, and services that listen on
# IPv4 only reset that connection; 127.0.0.1 always goes over IPv4.
HOST_ADDRESS_NOTE = (
    "Host addresses use 127.0.0.1. With IPv6 enabled in Docker, localhost can reach "
    "a service's IPv6 address, and services that listen on IPv4 only reset the "
    "connection. localhost works when Docker's IPv6 is off."
)


def print_explain_panel(details: ProfileDetails):
    """
    Format and print the detailed Profile Inspector panel.

    Args:
        details (ProfileDetails): The profile to describe.
    """
    profile = details.profile
    deps = [p for p in details.starts if p != profile] or ["None"]
    deps_str = ", ".join(f"[yellow]{d}[/yellow]" for d in deps)
    services = details.services
    volumes = details.volumes
    usage = details.usage
    if details.usage_missing:
        usage = f"• No specific usage guide for profile: {profile}"
    role = details.role

    # Container Context (Substring matching)
    container_roles = {
        "odctl/postgres": "PostgreSQL with pgvector, pg_textsearch and PostGIS",
        "seaweedfs": "Object Storage (S3 API)",
        "zulu-openjdk": "Iceberg REST Catalog",
        "odctl/deps": "Dependency Initializer",
        "flink": "Flink Stream Processing Node",
        "apache/kafka": "Event Broker / Kafka Connect",
        "karapace": "Schema Registry",
        "kafka-ui": "Kafka Dashboard",
        "elasticsearch": "OpenMetadata Search Backend",
        "openmetadata/server": "OpenMetadata Server",
        "openmetadata/ingestion": "OpenMetadata Ingestion Pipeline",
        "odctl/airflow": "Airflow Orchestrator",
        "odctl/mlflow": "MLflow Tracking and Model Server",
        "evidently-service": "ML Monitoring (Evidently UI)",
        "temporalio/temporal": "Temporal Development Server and Web UI",
        "marquez-web": "Lineage Dashboard",
        "marquezproject/marquez": "Lineage API Server",
        "otel-lgtm": "Telemetry: OTLP, Prometheus, Tempo, Loki, Grafana",
        "odctl/spark": "Spark Processing Node",
        "clickhouse-keeper": "Consensus Node",
        "clickhouse-server": "Analytical Database (OLAP)",
        "fluss": "Streaming Storage Engine",
        "valkey": "In-Memory Cache & Vector DB",
        "trinodb/trino": "Federated SQL Engine",
        "metabase": "BI Dashboard",
    }

    with_images = [svc for svc in services if svc.image]
    if with_images:
        services_list = []
        for svc in with_images:
            img = svc.image or ""
            role_desc = "Service Container"
            for key, desc in container_roles.items():
                if key in img:
                    role_desc = desc
                    break

            services_list.append(
                f"  📦 [magenta]{svc.name.ljust(22, ' ')}[/magenta] ([green]{img}[/green])\n      ↳ [dim]{role_desc}[/dim]"
            )
        services_str = "\n".join(services_list)
    else:
        services_str = (
            "\n".join(f"  📦 [magenta]{svc.name}[/magenta]" for svc in services)
            if services
            else "  None"
        )

    # Volumes Context
    volumes_str = (
        "\n".join(f"  💾 [green]{v}[/green]" for v in volumes) if volumes else "  None"
    )
    if volumes:
        volumes_str += (
            "\n  [dim italic](Use 'odctl down -v' to wipe these volumes)[/dim italic]"
        )

    # Port Context (Host vs Internal Routing)
    ports_list = []
    for spec in details.port_specs:
        parts = spec.split(":")
        svc_name = parts[0]

        # Parse Host vs Container mapping (for example, flink-sql-gateway:127.0.0.1:8084:8083)
        if len(parts) >= 3:
            host_port = parts[-2]
            container_port = parts[-1]
        elif len(parts) == 2:
            host_port = parts[1]
            container_port = parts[1]
        else:
            continue

        ports_list.append(
            f"  🔌 Host [bold blue]{host_port.ljust(5, ' ')}[/bold blue] → Container [cyan]{svc_name}:{container_port}[/cyan]"
        )
    ports_str = "\n".join(ports_list) if ports_list else "  None"

    # Constructing the Output
    role_section = f"\n[bold]Architecture Role:[/bold]\n{role}\n" if role else ""
    usage_section = (
        # Usage text is plain: escape it, or Rich reads feast[duckdb,...] as markup.
        f"\n[bold green]🚀 How to Use It:[/bold green]\n{escape(usage)}\n"
        if usage
        else ""
    )

    body = f"""
[bold]Parent Stack:[/bold] {details.stack}
[bold]Compose File:[/bold] {details.compose_file}

[bold]Description:[/bold]
{details.description}
{role_section}
[bold]Requires Dependencies:[/bold]
  {deps_str}

[bold]Persistent Volumes:[/bold]
{volumes_str}

[bold]Containers (Images):[/bold]
{services_str}

[bold]Network Mapping (Host → Docker):[/bold]
{ports_str}
{usage_section}[bold]Note:[/bold]
[dim]{HOST_ADDRESS_NOTE}[/dim]"""

    console.print(
        Panel(
            body.strip(),
            title=f"🔍 Profile Inspector: [bold cyan]{profile}[/bold cyan]",
            border_style="cyan",
        )
    )


def print_dry_run(
    execution_plan: Dict[str, List[str]],
    is_teardown: bool = False,
    volumes: Optional[Dict[str, List[str]]] = None,
):
    """
    Print the dry run execution or teardown plan to the console.

    Args:
        execution_plan (Dict[str, List[str]]): The resolved mapping of files to profiles.
        is_teardown (bool, optional): If True, formats the output as a teardown plan
                                      instead of a startup plan. Defaults to False.
        volumes (Optional[Dict[str, List[str]]], optional): For a teardown, the
            volumes to remove, by compose file, each as the text printed after
            `Remove Volume:`. Defaults to None, which prints no volumes.
    """
    title = "Dry Run Teardown Plan" if is_teardown else "Dry Run Execution Plan"
    color = "red" if is_teardown else "yellow"

    console.print(Panel(f"[bold {color}]{title}[/bold {color}]"))
    volumes = volumes or {}
    for file, profs in execution_plan.items():
        if is_teardown:
            console.print(f"🛑 [cyan]{file}[/cyan]")
            for p in profs:
                console.print(f"  └─ 💥 Stop Profile: [bold red]{p}[/bold red]")
            for name in volumes.get(file, []):
                console.print(f"  └─ 🗑  Remove Volume: [bold red]{name}[/bold red]")
        else:
            layer = (
                "Infrastructure Layer"
                if any(x in profs for x in ["deps", "postgres", "storage", "catalog"])
                else "Target Stack"
            )
            console.print(f"📦 [cyan]{file}[/cyan] ({layer})")
            for p in profs:
                console.print(f"  └─ 🚀 Profile: [bold green]{p}[/bold green]")


def format_docker_error(exc: Exception, max_lines: int = 10) -> str:
    """
    Reduce a python_on_whales DockerException to the part worth reading.

    str() on one of these returns four lines of boilerplate that name the full
    command and then say the output "can be found above the stacktrace (it
    wasn't captured)". That is accurate but useless: compose runs with
    capture_stderr=False, so Docker has already printed the real error to the
    terminal, and repeating that it is missing buries it.

    Args:
        exc (Exception): The exception raised by a compose call.
        max_lines (int, optional): How many trailing stderr lines to keep. Defaults to 10.

    Returns:
        str: The captured stderr if there is any, otherwise the exit code alone.
    """
    stderr = getattr(exc, "stderr", None)
    if stderr:
        lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
        return "\n".join(lines[-max_lines:])

    code = getattr(exc, "return_code", None)
    if code is not None:
        return f"docker compose exited with code {code}. Its output is above."

    return str(exc)


def print_error(message: str, details: Optional[str] = None, show_tip: bool = False):
    """
    Print a standardized error message to stdout, or to stderr under `--json`.

    Args:
        message (str): The primary error message.
        details (Optional[str], optional): Additional technical details or exceptions. Defaults to None.
        show_tip (bool, optional): If True, appends a troubleshooting tip regarding Docker logs. Defaults to False.
    """
    out = _message_console()
    out.print(f"[bold red]Error:[/bold red] {message}")
    if details:
        out.print(f"[red]Details:[/red] {details}")
    if show_tip:
        out.print(
            "\n[yellow]Tip:[/yellow] Docker's own message is printed above this error."
        )
        out.print(
            "A pull failure names the image and leaves no container behind. "
            "For a container that started and then failed, "
            "run [cyan]docker ps -a[/cyan] and [cyan]docker logs <name>[/cyan]."
        )


def print_success(message: str):
    """
    Print a standardized success message to the console.

    Args:
        message (str): The success message to display.
    """
    console.print(f"[bold green]✓ {message}[/bold green]")


def print_step(message: str):
    """
    Print an intermediate loading or action step to the console.

    Args:
        message (str): The step message to display.
    """
    console.print(f"[bold yellow]⏳ {message}[/bold yellow]")


def print_info(message: str, style: str = "cyan"):
    """
    Print general information to stdout, or to stderr under `--json`, with a specific style.

    Args:
        message (str): The info message to display.
        style (str, optional): The Rich formatting style to apply. Defaults to "cyan".
    """
    _message_console().print(f"[{style}]{message}[/{style}]")


def print_ps_table(report: PsReport):
    """
    Format and print the list of running containers as a status table.

    Args:
        report (PsReport): The active profiles and the containers to show.
    """
    if report.active_profiles:
        console.print(
            f"🌟 [bold]Active Profiles:[/bold] [green]{', '.join(report.active_profiles)}[/green]\n"
        )

    if not report.containers:
        print_info(
            "No containers found for the requested profiles. Are they running?",
            style="yellow",
        )
        return

    table = Table(header_style="bold cyan", border_style="cyan")
    table.add_column("Container", style="magenta", no_wrap=True)
    table.add_column("Service", style="yellow", no_wrap=True)
    table.add_column("State", style="bold")
    table.add_column("Health")
    table.add_column("Ports", style="blue")

    for c in report.containers:
        state_color = (
            "green"
            if c.state == "running"
            else "red"
            if c.state in ["exited", "dead"]
            else "yellow"
        )
        state_str = f"[{state_color}]{c.state}[/{state_color}]"

        health_str = "-"
        if c.health:
            h_color = (
                "green"
                if c.health == "healthy"
                else "red"
                if c.health == "unhealthy"
                else "yellow"
            )
            health_str = f"[{h_color}]{c.health}[/{h_color}]"

        ports_str = (
            ", ".join(f"{p.host} → {p.container}/{p.protocol}" for p in c.ports) or "-"
        )

        table.add_row(c.name, c.service or "-", state_str, health_str, ports_str)

    console.print(table)


def print_package_info(info: Info):
    """
    Display system-wide ODCTL configuration and Docker daemon health status.

    Args:
        info (Info): The version and Docker state to show.
    """
    docker_status = (
        "[green]✅ Reachable[/green]"
        if info.docker.reachable
        else "[red]❌ Not Reachable[/red]"
    )

    console.print("\n[bold cyan]Open Data Stack (ODCTL)[/bold cyan]")
    console.print(f"CLI Version:   {info.cli_version}")
    console.print(f"Docker Daemon: {docker_status}\n")
