from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dml.docker import (
    get_stack_details,
    is_docker_running,
    launch_stack,
    pull_stack_images,
    stop_stack,
)
from dml.planner import build_execution_plan, get_profile_map
from dml.registry import load_registry
from dml.workspace import get_workspace_dir, init_workspace

app = typer.Typer(
    help="DML CLI: Orchestrator for Open DataML Stack",
    no_args_is_help=True,
    epilog="""
[bold]Examples:[/bold]
  Launch specific profiles:
  $ [cyan]dml up clickhouse flink1 kafka[/cyan]

  Pre-fetch images without starting:
  $ [cyan]dml pull --all[/cyan]

  Destroy everything and wipe data:
  $ [cyan]dml down --all --volumes[/cyan]
""",
)
console = Console()


@app.callback()
def main():
    """Semantic Orchestrator for the Open DataML Stack."""
    pass


@app.command(name="list")
def list_profiles(
    deep: bool = typer.Option(False, "--deep", "-d", help="Show port mappings"),
):
    """List all available profiles and their capabilities."""
    try:
        registry = load_registry()
        table = Table(header_style="bold")
        table.add_column("Profile", style="green", no_wrap=True, vertical="middle")
        table.add_column("Parent Stack", style="cyan", vertical="middle")
        table.add_column("Description", max_width=75, vertical="middle")

        if deep:
            table.add_column(
                "Services", style="magenta", max_width=45, vertical="middle"
            )
            table.add_column(
                "Port Mappings", style="blue", max_width=45, vertical="middle"
            )

        for stack_id, config in registry.stacks.items():
            for i, profile in enumerate(config.profiles):
                display_stack = stack_id if i == 0 else ""
                display_desc = config.description if i == 0 else ""
                row = [profile, display_stack, display_desc]

                if deep:
                    services, ports, _ = get_stack_details(config.file, [profile])
                    row.append(", ".join(services) if services else "N/A")
                    row.append(", ".join(ports) if ports else "N/A")

                table.add_row(*row)
            table.add_section()

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def explain(profile: str = typer.Argument(..., help="The profile to inspect")):
    """Explain the details, services, images, and dependencies of a specific profile."""
    registry = load_registry()
    profile_map = get_profile_map()

    if profile not in profile_map:
        console.print(
            f"[bold red]Error:[/bold red] Profile '{profile}' not found in registry."
        )
        raise typer.Exit(1)

    stack_id = profile_map[profile]["stack_id"]
    stack = registry.stacks[stack_id]

    # We use your existing get_stack_details exactly as it is!
    services, ports, images = get_stack_details(stack.file, [profile])

    deps_str = ", ".join(
        f"[yellow]{d}[/yellow]" for d in (stack.depends_on or ["None"])
    )

    # Check if we have valid images to parse
    if images and " -> " in images[0]:
        services_str = "\n".join(
            f"  📦 [magenta]{item.split(' -> ')[0].ljust(20, ' ')}[/magenta] ([green]{item.split(' -> ')[1]}[/green])"
            for item in images
        )
    else:
        # Fallback just in case
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
[bold]Compose File:[/bold] {stack.file}

[bold]Description:[/bold] 
{stack.description}

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


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Recreate workspace, wiping modifications"
    ),
):
    """Initialize a local .dml workspace for custom configurations."""
    if force and get_workspace_dir().exists():
        typer.confirm(
            "⚠️  This will wipe out all local modifications in your .dml/ directory. Are you sure?",
            abort=True,
        )
    init_workspace(force=force)
    console.print(
        "[bold green]✓ Workspace initialized![/bold green] You can now edit any file in ./.dml/"
    )


@app.command()
def pull(
    profiles: Optional[List[str]] = typer.Argument(
        None, help="Profiles to pull images for"
    ),
    all: bool = typer.Option(
        False, "--all", help="Pull all images for all profiles in the registry"
    ),
):
    """Pre-fetch Docker images without starting the containers."""
    if not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)

    execution_plan = build_execution_plan(
        profiles=profiles, all_profiles=all, resolve_deps=True
    )

    console.print("[bold cyan]📥 Pre-fetching Docker images...[/bold cyan]")
    for file, profs in execution_plan.items():
        console.print(
            f"Fetching images for [yellow]{file}[/yellow] (profiles: {', '.join(profs)})..."
        )
        try:
            pull_stack_images(file, profs)
        except Exception as e:
            console.print(f"[bold red]Failed to pull images for {file}:[/bold red] {e}")
            raise typer.Exit(1)
    console.print("[bold green]✓ All images pulled successfully![/bold green]")


@app.command()
def up(
    profiles: List[str] = typer.Argument(..., help="One or more profiles to launch"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print execution plan without launching"
    ),
):
    """Launch DataML profiles."""
    if not dry_run and not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)

    execution_plan = build_execution_plan(
        profiles=profiles, all_profiles=False, resolve_deps=True
    )

    if dry_run:
        console.print(Panel("[bold yellow]Dry Run Execution Plan[/bold yellow]"))
        for file, profs in execution_plan.items():
            layer = (
                "Infrastructure Layer"
                if "base" in profs or "deps" in profs
                else "Target Stack"
            )
            console.print(f"📦 [cyan]{file}[/cyan] ({layer})")
            for p in profs:
                console.print(f"  └─ 🚀 Profile: [bold green]{p}[/bold green]")
        return

    for file, profs in execution_plan.items():
        is_base = "base" in profs or "deps" in profs
        prefix = "🧱 Infrastructure" if is_base else "🚀 Target"

        console.print(
            f"📥 Pulling images for {prefix} ([cyan]{', '.join(profs)}[/cyan])..."
        )
        pull_stack_images(file, profs)

        console.print(f"⚙️  Launching {prefix} ([cyan]{', '.join(profs)}[/cyan])...")
        try:
            launch_stack(file, profs)
        except Exception as e:
            err_msg = str(e)
            console.print(f"\n[bold red]❌ Failed to start {file}[/bold red]")

            # Hide the messy python-on-whales exception string and give actionable advice
            if "The command executed was" in err_msg:
                console.print(
                    "[yellow]Tip:[/yellow] A container failed to reach a healthy state or crashed on startup."
                )
                console.print(
                    "Run [cyan]docker ps -a[/cyan] or check Docker Desktop to inspect the logs."
                )
            else:
                console.print(f"[red]Details:[/red] {err_msg}")

            raise typer.Exit(1)

    console.print(
        "[bold green]✓ All requested profiles successfully started![/bold green]"
    )


@app.command()
def down(
    profiles: Optional[List[str]] = typer.Argument(None, help="Profiles to stop"),
    all: bool = typer.Option(
        False, "--all", help="Stop all stacks defined in registry"
    ),
    volumes: bool = typer.Option(
        False, "--volumes", "-v", help="Remove named volumes (wipes data!)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print teardown plan without executing"
    ),
):
    """Stop and remove profile containers and networks."""
    if not dry_run and not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)

    if all and volumes and not dry_run:
        typer.confirm(
            "⚠️  This will destroy ALL profiles and WIPE ALL LOCAL DATA. Are you sure?",
            abort=True,
        )

    execution_plan = build_execution_plan(
        profiles=profiles, all_profiles=all, resolve_deps=False
    )

    # For teardown, reverse the plan so dependents are destroyed before base infrastructure
    execution_plan = dict(reversed(list(execution_plan.items())))

    if dry_run:
        console.print(Panel("[bold yellow]Dry Run Teardown Plan[/bold yellow]"))
        for file, profs in execution_plan.items():
            console.print(f"🛑 [cyan]{file}[/cyan]")
            for p in profs:
                console.print(f"  └─ 💥 Stop Profile: [bold red]{p}[/bold red]")
        if volumes:
            console.print("\n[bold red]⚠️ Volumes will be destroyed.[/bold red]")
        return

    for file, profs in execution_plan.items():
        console.print(f"🛑 Stopping [cyan]{', '.join(profs)}[/cyan]...")
        try:
            stop_stack(file, profs, remove_volumes=volumes)
        except Exception as e:
            console.print(f"[bold red]Failed to stop {file}:[/bold red] {e}")
            raise typer.Exit(1)

    console.print("[bold green]✓ Teardown complete.[/bold green]")


if __name__ == "__main__":
    app()
