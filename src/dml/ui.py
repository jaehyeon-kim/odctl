from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dml.docker import is_docker_running

console = Console()


def print_profile_table(registry: Any, deep: bool, get_details_func: Any):
    """Formats and prints the list of available profiles."""
    table = Table(header_style="bold")
    table.add_column("Profile", style="green", no_wrap=True, vertical="middle")
    table.add_column("Parent Stack", style="cyan", vertical="middle")
    table.add_column("Description", max_width=60, vertical="middle")

    if deep:
        table.add_column("Services", style="magenta", max_width=45, vertical="middle")
        table.add_column("Port Mappings", style="blue", max_width=55, vertical="middle")

    for stack_id, config in registry.stacks.items():
        display_group_name = config.parent if config.parent else stack_id

        for i, profile in enumerate(config.profiles):
            display_stack = display_group_name if i == 0 else ""
            display_desc = config.description if i == 0 else ""
            row = [profile, display_stack, display_desc]

            if deep:
                # Absorb the newly returned volumes with an underscore
                services, ports, _, _ = get_details_func(config.file, [profile])
                row.append(", ".join(services) if services else "N/A")
                row.append(", ".join(ports) if ports else "N/A")

            table.add_row(*row)
        table.add_section()
    console.print(table)


def print_explain_panel(
    profile: str,
    stack_id: str,
    stack_file: str,
    description: str,
    deps: List[str],
    services: List[str],
    ports: List[str],
    images: List[str],
    volumes: List[str],
    role: Optional[str] = None,
    usage: Optional[str] = None,
):
    """Formats and prints the detailed Profile Inspector panel."""

    deps_str = ", ".join(f"[yellow]{d}[/yellow]" for d in deps)

    # Container Context (Substring matching)
    container_roles = {
        "pgvector": "Unified Metadata & Vector DB",
        "dbgate": "Database Inspection UI",
        "seaweedfs": "Object Storage (S3 API)",
        "iceberg-rest": "Iceberg REST Catalog",
        "open-dataml-stack/pyiceberg": "PyIceberg CLI Proxy",
        "open-dataml-stack/deps": "Dependency Initializer",
        "flink": "Flink Stream Processing Node",
        "apache/kafka": "Event Broker / Kafka Connect",
        "karapace": "Schema Registry",
        "kafka-ui": "Kafka Dashboard",
        "elasticsearch": "OpenMetadata Search Backend",
        "openmetadata/server": "OpenMetadata Server",
        "openmetadata/ingestion": "OpenMetadata Ingestion Pipeline",
        "amazon/aws-cli": "Airflow DAG S3 Sync",
        "open-dataml-stack/airflow": "Airflow Orchestrator",
        "open-dataml-stack/mlflow": "MLflow Tracking Server",
        "open-dataml-stack/feast": "Feast Feature Server",
        "marquez-web": "Lineage Dashboard",
        "marquezproject/marquez": "Lineage API Server",
        "prometheus": "Telemetry Metrics Server",
        "alertmanager": "Alerting Server",
        "grafana": "Observability Dashboard",
        "open-dataml-stack/spark": "Spark Processing Node",
        "clickhouse-keeper": "Consensus Node",
        "clickhouse-server": "Analytical Database (OLAP)",
        "fluss": "Streaming Storage Engine",
        "valkey": "In-Memory Cache",
        "trinodb/trino": "Federated SQL Engine",
        "metabase": "BI Dashboard",
    }

    if images and " -> " in images[0]:
        services_list = []
        for item in images:
            name, img = item.split(" -> ")
            role_desc = "Service Container"
            for key, desc in container_roles.items():
                if key in img:
                    role_desc = desc
                    break

            services_list.append(
                f"  📦 [magenta]{name.ljust(22, ' ')}[/magenta] ([green]{img}[/green])\n      ↳ [dim]{role_desc}[/dim]"
            )
        services_str = "\n".join(services_list)
    else:
        services_str = (
            "\n".join(f"  📦 [magenta]{s}[/magenta]" for s in services)
            if services
            else "  None"
        )

    # Volumes Context
    volumes_str = (
        "\n".join(f"  💾 [green]{v}[/green]" for v in volumes) if volumes else "  None"
    )
    if volumes:
        volumes_str += (
            "\n  [dim italic](Use 'dml down -v' to wipe these volumes)[/dim italic]"
        )

    # Port Context (Host vs Internal Routing)
    ports_list = []
    for p in ports:
        parts = p.split(":")
        svc_name = parts[0]

        # Parse Host vs Container mapping (e.g., flink-sql-gateway:8084:8083)
        if len(parts) >= 3:
            host_port = parts[1]
            container_port = parts[2]
        elif len(parts) == 2:
            host_port = parts[1]
            container_port = parts[1]
        else:
            continue

        ports_list.append(
            f"  🔌 Host [bold blue]{host_port.ljust(5, ' ')}[/bold blue] ➡️  Container [cyan]{svc_name}:{container_port}[/cyan]"
        )
    ports_str = "\n".join(ports_list) if ports_list else "  None"

    # Constructing the Output
    role_section = f"\n[bold]Architecture Role:[/bold]\n{role}\n" if role else ""
    usage_section = (
        f"\n[bold green]🚀 How to Use It:[/bold green]\n{usage}\n" if usage else ""
    )

    details = f"""
[bold]Parent Stack:[/bold] {stack_id}
[bold]Compose File:[/bold] {stack_file}

[bold]Description:[/bold] 
{description}
{role_section}
[bold]Requires Dependencies:[/bold] 
  {deps_str}

[bold]Persistent Volumes:[/bold]
{volumes_str}

[bold]Containers (Images):[/bold]
{services_str}

[bold]Network Mapping (Host ➡️  Docker):[/bold]
{ports_str}
{usage_section}"""

    console.print(
        Panel(
            details.strip(),
            title=f"🔍 Profile Inspector: [bold cyan]{profile}[/bold cyan]",
            border_style="cyan",
        )
    )


def print_dry_run(execution_plan: Dict[str, List[str]], is_teardown: bool = False):
    """Prints the dry run execution or teardown plan."""
    title = "Dry Run Teardown Plan" if is_teardown else "Dry Run Execution Plan"
    color = "red" if is_teardown else "yellow"

    console.print(Panel(f"[bold {color}]{title}[/bold {color}]"))
    for file, profs in execution_plan.items():
        if is_teardown:
            console.print(f"🛑 [cyan]{file}[/cyan]")
            for p in profs:
                console.print(f"  └─ 💥 Stop Profile: [bold red]{p}[/bold red]")
        else:
            layer = (
                "Infrastructure Layer"
                if any(x in profs for x in ["base", "deps"])
                else "Target Stack"
            )
            console.print(f"📦 [cyan]{file}[/cyan] ({layer})")
            for p in profs:
                console.print(f"  └─ 🚀 Profile: [bold green]{p}[/bold green]")


def print_error(message: str, details: Optional[str] = None, show_tip: bool = False):
    """Standardized error display."""
    console.print(f"[bold red]Error:[/bold red] {message}")
    if details:
        console.print(f"[red]Details:[/red] {details}")
    if show_tip:
        console.print(
            "\n[yellow]Tip:[/yellow] A container failed to reach a healthy state or crashed on startup."
        )
        console.print(
            "Run [cyan]docker ps -a[/cyan] or check Docker Desktop to inspect the logs."
        )


def print_success(message: str):
    console.print(f"[bold green]✓ {message}[/bold green]")


def print_step(message: str):
    """Prints an intermediate loading/action step."""
    console.print(f"[bold yellow]⏳ {message}[/bold yellow]")


def print_info(message: str, style: str = "cyan"):
    console.print(f"[{style}]{message}[/{style}]")


def print_ps_table(containers: List[Any]):
    """Formats and prints the list of running containers."""
    if not containers:
        print_info(
            "No containers found for the requested profiles. Are they running?",
            style="yellow",
        )
        return

    table = Table(header_style="bold cyan", border_style="cyan")
    table.add_column("Container Name", style="magenta", no_wrap=True)
    # 👇 Add this new column so the user knows exactly what to type for 'dml logs -s'
    table.add_column("Service", style="yellow", no_wrap=True)
    table.add_column("State", style="bold")
    table.add_column("Health")
    table.add_column("Ports", style="blue")

    sorted_containers = sorted(containers, key=lambda c: c.name)

    for c in sorted_containers:
        # Extract the exact Compose Service name
        labels = c.config.labels if c.config and c.config.labels else {}
        svc_name = labels.get("com.docker.compose.service", "-")

        # Format State
        state = c.state.status
        state_color = (
            "green"
            if state == "running"
            else "red"
            if state in ["exited", "dead"]
            else "yellow"
        )
        state_str = f"[{state_color}]{state}[/{state_color}]"

        # Format Health
        health_str = "-"
        if c.state.health:
            h_status = c.state.health.status
            h_color = (
                "green"
                if h_status == "healthy"
                else "red"
                if h_status == "unhealthy"
                else "yellow"
            )
            health_str = f"[{h_color}]{h_status}[/{h_color}]"

        # Format Ports
        ports_list = []
        if c.network_settings and c.network_settings.ports:
            for c_port, bindings in c.network_settings.ports.items():
                if bindings:
                    for b in bindings:
                        host_port = b.get("HostPort")
                        if host_port:
                            mapping = f"{host_port} ➡️  {c_port}"
                            if mapping not in ports_list:
                                ports_list.append(mapping)

        ports_str = ", ".join(ports_list) if ports_list else "-"

        table.add_row(c.name, svc_name, state_str, health_str, ports_str)

    console.print(table)


def print_package_info():
    """Display system-wide DML configuration and Docker health."""
    try:
        # Change this to whatever your pip package name actually is
        cli_version = version("dml-cli")
    except PackageNotFoundError:
        cli_version = "Development (Local)"

    docker_status = (
        "[green]✅ Reachable[/green]"
        if is_docker_running()
        else "[red]❌ Not Reachable[/red]"
    )

    # You can format this using a Rich panel in ui.py, but here is the base logic
    console.print("\n[bold cyan]Open DataML Stack (DML)[/bold cyan]")
    console.print(f"CLI Version:   {cli_version}")
    console.print(f"Docker Daemon: {docker_status}\n")
