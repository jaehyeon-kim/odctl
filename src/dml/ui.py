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
    table.add_column("Description", max_width=75, vertical="middle")

    if deep:
        table.add_column("Services", style="magenta", max_width=45, vertical="middle")
        table.add_column("Port Mappings", style="blue", max_width=45, vertical="middle")

    for stack_id, config in registry.stacks.items():
        for i, profile in enumerate(config.profiles):
            display_stack = stack_id if i == 0 else ""
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
):
    """Formats and prints the detailed Profile Inspector panel."""
    deps_str = ", ".join(f"[yellow]{d}[/yellow]" for d in deps)

    if images and " -> " in images[0]:
        services_str = "\n".join(
            f"  📦 [magenta]{item.split(' -> ')[0].ljust(20, ' ')}[/magenta] ([green]{item.split(' -> ')[1]}[/green])"
            for item in images
        )
    else:
        services_str = (
            "\n".join(f"  📦 [magenta]{s}[/magenta]" for s in services)
            if services
            else "  None"
        )

    ports_str = (
        "\n".join(f"  🔌 [blue]{p}[/blue]" for p in ports) if ports else "  None"
    )

    details = f"""
[bold]Parent Stack:[/bold] {stack_id}
[bold]Compose File:[/bold] {stack_file}

[bold]Description:[/bold] 
{description}

[bold]Requires Dependencies:[/bold] 
  {deps_str}

[bold]Containers (Images):[/bold]
{services_str}

[bold]Exposed Host Ports:[/bold]
{ports_str}
"""
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
