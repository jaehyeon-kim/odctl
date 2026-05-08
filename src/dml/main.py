from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dml.docker import (
    get_stack_details,
    is_docker_running,
    launch_stack,
    pull_stack_images,
    stop_stack,
)
from dml.registry import load_registry
from dml.workspace import init_workspace

app = typer.Typer(
    help="DML CLI: Semantic Orchestrator for DataML Stacks",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


@app.callback()
def main():
    """Semantic Orchestrator for the Open DataML Stack."""
    pass


@app.command(name="list")
def list_stacks(
    deep: bool = typer.Option(False, "--deep", "-d", help="Show port mappings"),
):
    """List all available stacks and their capabilities."""
    try:
        registry = load_registry()
        table = Table(header_style="bold")

        table.add_column("Stack ID", style="cyan", no_wrap=True, vertical="middle")
        table.add_column(
            "Description", max_width=50 if deep else 100, vertical="middle"
        )
        table.add_column("Profiles", style="green", vertical="middle")
        table.add_column("Capacities", style="yellow", vertical="middle")
        if deep:
            table.add_column(
                "Services", style="magenta", max_width=50, vertical="middle"
            )
            table.add_column(
                "Port Mappings", style="blue", max_width=50, vertical="middle"
            )

        stacks_items = list(registry.stacks.items())
        for idx, (stack_id, config) in enumerate(stacks_items):
            # Fallback in case a stack has no profiles defined
            profiles = config.profiles if config.profiles else [""]

            for i, profile in enumerate(profiles):
                # Only show stack-level details on the first row of each stack
                display_id = stack_id if i == 0 else ""
                display_desc = config.description if i == 0 else ""
                display_caps = ", ".join(config.capacities) if i == 0 else ""

                row = [display_id, display_desc, profile, display_caps]

                if deep:
                    # Query services and ports only for this specific profile
                    if profile:
                        services, ports = get_stack_details(config.file, [profile])
                        row.append(", ".join(services) if services else "N/A")
                        row.append(", ".join(ports) if ports else "N/A")
                    else:
                        row.extend(["N/A", "N/A"])

                table.add_row(*row)

            # Add a separator line between different stacks
            if idx < len(stacks_items) - 1:
                table.add_section()

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def init():
    """Initialize a local .dml workspace for custom configurations."""
    init_workspace()
    console.print(
        "[bold green]✓ Workspace initialized![/bold green] You can now edit any file in ./.dml/"
    )


@app.command()
def up(stack_name: str):
    """Launch a DataML stack."""
    if not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)

    registry = load_registry()
    if stack_name not in registry.stacks:
        console.print(f"[bold red]Error:[/bold red] Stack '{stack_name}' not found.")
        raise typer.Exit(1)

    stack = registry.stacks[stack_name]

    # Boot Sequencing: Ensure base is up if we are starting something else
    if stack_name != "base":
        console.print("📦 Checking [cyan]base[/cyan] infrastructure layer...")
        base_stack = registry.stacks["base"]

        # Pull and launch base
        pull_stack_images(base_stack.file, base_stack.profiles)
        launch_stack(base_stack.file, base_stack.profiles)
        console.print("[green]✓ Base layer is ready.[/green]")

    # Pull Target Images
    console.print(f"📥 Pulling images for [bold cyan]{stack_name}[/bold cyan]...")
    pull_stack_images(stack.file, stack.profiles)

    # Launch Target Stack
    console.print(f"🚀 Launching [bold cyan]{stack_name}[/bold cyan]...")
    try:
        launch_stack(stack.file, stack.profiles)
        console.print(f"[bold green]✓ {stack_name} successfully started![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to start {stack_name}:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def down(
    stack_name: Optional[str] = typer.Argument(None, help="Stack to stop"),
    all: bool = typer.Option(
        False, "--all", help="Stop all stacks defined in registry"
    ),
    volumes: bool = typer.Option(
        False, "--volumes", "-v", help="Remove named volumes (wipes data!)"
    ),
):
    """Stop and remove stack containers and networks."""
    if not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)

    registry = load_registry()

    # 1. Handle "Stop All" logic
    if all:
        # Reverse the order so dependent stacks stop before the base layer
        stack_ids = list(registry.stacks.keys())[::-1]
        console.print("[bold yellow]Stopping all stacks...[/bold yellow]")
        for s_id in stack_ids:
            stack = registry.stacks[s_id]
            console.print(f"⠋ Stopping {s_id}...")
            stop_stack(stack.file, stack.profiles, remove_volumes=volumes)
        console.print("[bold green]✓ All stacks stopped.[/bold green]")
        return

    # 2. Handle single stack logic
    if not stack_name:
        console.print(
            "[bold red]Error:[/bold red] Please specify a stack name or use --all"
        )
        raise typer.Exit(1)

    if stack_name not in registry.stacks:
        console.print(f"[bold red]Error:[/bold red] Stack '{stack_name}' not found.")
        raise typer.Exit(1)

    stack = registry.stacks[stack_name]
    console.print(f"🛑 Stopping [bold cyan]{stack_name}[/bold cyan]...")

    try:
        stop_stack(stack.file, stack.profiles, remove_volumes=volumes)
        console.print(f"[bold green]✓ {stack_name} stopped successfully.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to stop {stack_name}:[/bold red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
