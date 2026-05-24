from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
        # Decide the display name: Use config.parent if it exists, otherwise use stack_id
        display_group_name = config.parent if config.parent else stack_id

        for i, profile in enumerate(config.profiles):
            display_stack = display_group_name if i == 0 else ""
            display_desc = config.description if i == 0 else ""
            row = [profile, display_stack, display_desc]

            if deep:
                services, ports, _ = get_details_func(config.file, [profile])
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
    role: Optional[str] = None,
    usage: Optional[str] = None,
):
    """Formats and prints the detailed Profile Inspector panel."""

    # Dependency Context
    deps_str = ", ".join(f"[yellow]{d}[/yellow]" for d in deps)

    # Container Context (Mapping images to their roles)
    container_roles = {
        "apache/kafka": "Event Broker / Connect Worker",
        "ghcr.io/kafbat/kafka-ui": "Web Dashboard",
        "ghcr.io/aiven-open/karapace": "Schema Registry API",
        "chrislusf/seaweedfs": "Object Storage Engine",
        "tabulario/iceberg-rest": "REST API Gateway",
        "ghcr.io/jaehyeon-kim/open-dataml-stack/pyiceberg": "Headless CLI Proxy",
        "postgres": "Metadata Database",
        "getdbgate/dbgate": "Database Web UI",
    }

    if images and " -> " in images[0]:
        services_list = []
        for item in images:
            name, img = item.split(" -> ")
            base_img = img.split(":")[0]  # Strip the tag for matching
            role_desc = container_roles.get(base_img, "Service Container")
            services_list.append(
                f"  📦 [magenta]{name.ljust(15, ' ')}[/magenta] ([green]{img}[/green]) ➡️ [dim]{role_desc}[/dim]"
            )
        services_str = "\n".join(services_list)
    else:
        services_str = (
            "\n".join(f"  📦 [magenta]{s}[/magenta]" for s in services)
            if services
            else "  None"
        )

    # 3. Port Context
    port_context = {
        "8333": "S3 API Endpoint (Boto3/Spark)",
        "8888": "Filer Web UI (Browser)",
        "9333": "Master Server API",
        "8181": "Iceberg REST API",
        "5432": "PostgreSQL DB Port",
        "3000": "DbGate Web UI",
        "8086": "Kafka Web UI",
        "8081": "Karapace Schema Registry API",
        "8083": "Kafka Connect API",
        "9092": "Kafka Broker 1 (External)",
        "9093": "Kafka Broker 2 (External)",
        "9094": "Kafka Broker 3 (External)",
        "29092": "Kafka Broker 1 (Minikube/Internal)",
        "29093": "Kafka Broker 2 (Minikube/Internal)",
        "29094": "Kafka Broker 3 (Minikube/Internal)",
    }

    ports_list = []
    for p in ports:
        # Example p: "seaweed:8333:8333" -> extract the last part
        host_port = p.split(":")[-1]
        context = port_context.get(host_port, "Mapped Port")
        ports_list.append(
            f"  🔌 [blue]{p.ljust(25, ' ')}[/blue] ➡️ [dim]{context}[/dim]"
        )
    ports_str = "\n".join(ports_list) if ports_list else "  None"

    # 4. Constructing the Output
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

[bold]Containers (Images):[/bold]
{services_str}

[bold]Exposed Host Ports:[/bold]
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


def print_info(message: str, style: str = "cyan"):
    console.print(f"[{style}]{message}[/{style}]")
