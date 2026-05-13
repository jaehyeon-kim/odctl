from typing import Dict, List, Optional

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
from dml.registry import load_registry
from dml.workspace import get_workspace_dir, init_workspace

app = typer.Typer(
    help="DML CLI: Orchestrator for Open DataML Stack",
    no_args_is_help=True,
    epilog="""
[bold]Examples:[/bold]
  Launch specific profiles:
  $ [cyan]dml up clickhouse flink1 kafka[/cyan]

  See what will be launched without actually starting containers:
  $ [cyan]dml up trino metabase --dry-run[/cyan]

  Stop specific profiles:
  $ [cyan]dml down kafka trino[/cyan]

  Destroy everything and wipe data:
  $ [cyan]dml down --all --volumes[/cyan]
""",
)
console = Console()


@app.callback()
def main():
    """Semantic Orchestrator for the Open DataML Stack."""
    pass


def _get_profile_map() -> Dict[str, dict]:
    """Creates a reverse lookup mapping a profile back to its stack config."""
    registry = load_registry()
    profile_map = {}
    for stack_id, config in registry.stacks.items():
        for profile in config.profiles:
            profile_map[profile] = {"stack_id": stack_id, "file": config.file}
    return profile_map


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
                # Only show the Parent Stack and Description on the first row of the group
                display_stack = stack_id if i == 0 else ""
                display_desc = config.description if i == 0 else ""

                row = [profile, display_stack, display_desc]

                if deep:
                    services, ports = get_stack_details(config.file, [profile])
                    row.append(", ".join(services) if services else "N/A")
                    row.append(", ".join(ports) if ports else "N/A")

                table.add_row(*row)

            # Add a horizontal line between different stacks for clean grouping
            table.add_section()

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def explain(profile: str = typer.Argument(..., help="The profile to inspect")):
    """Explain the details, services, and dependencies of a specific profile."""
    registry = load_registry()
    profile_map = _get_profile_map()

    if profile not in profile_map:
        console.print(
            f"[bold red]Error:[/bold red] Profile '{profile}' not found in registry."
        )
        raise typer.Exit(1)

    stack_id = profile_map[profile]["stack_id"]
    stack = registry.stacks[stack_id]

    # Query Docker Compose for the specific services and ports linked to this profile
    services, ports = get_stack_details(stack.file, [profile])

    # Format the dependencies
    deps = stack.depends_on if stack.depends_on else ["None"]
    deps_str = ", ".join(f"[yellow]{d}[/yellow]" for d in deps)

    # Format Services
    services_str = (
        "\n".join(f"  📦 [magenta]{s}[/magenta]" for s in services)
        if services
        else "  None"
    )

    # Format Ports
    ports_str = (
        "\n".join(f"  🔌 [blue]{p}[/blue]" for p in ports) if ports else "  None"
    )

    # Construct the Rich Panel content
    details = f"""
[bold]Parent Stack:[/bold] {stack_id}
[bold]Compose File:[/bold] {stack.file}

[bold]Description:[/bold] 
{stack.description}

[bold]Requires Dependencies:[/bold] 
  {deps_str}

[bold]Containers / Services:[/bold]
{services_str}

[bold]Exposed Host Ports:[/bold]
{ports_str}
"""
    # Print it beautifully
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
        False,
        "--force",
        "-f",
        help="Recreate the workspace, wiping any local modifications",
    ),
):
    """Initialize a local .dml workspace for custom configurations."""
    if force and get_workspace_dir().exists():
        typer.confirm(
            "⚠️ This will wipe out all local modifications in your .dml/ directory. Are you sure?",
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

    registry = load_registry()
    profile_map = _get_profile_map()

    execution_plan = {}

    if all:
        # Group all profiles by file
        for stack_id, config in registry.stacks.items():
            if config.file not in execution_plan:
                execution_plan[config.file] = []
            execution_plan[config.file].extend(config.profiles)
    else:
        if not profiles:
            console.print(
                "[bold red]Error:[/bold red] Please specify profile names or use --all"
            )
            raise typer.Exit(1)

        invalid_profiles = [p for p in profiles if p not in profile_map]
        if invalid_profiles:
            console.print(
                f"[bold red]Error:[/bold red] Unknown profiles: {', '.join(invalid_profiles)}"
            )
            raise typer.Exit(1)

        # Resolve dependencies just like `up`
        resolved_profiles = set(profiles)
        queue = list(profiles)

        while queue:
            current = queue.pop(0)
            stack_id = profile_map[current]["stack_id"]
            stack = registry.stacks[stack_id]
            for dep in stack.depends_on:
                if dep not in resolved_profiles:
                    resolved_profiles.add(dep)
                    queue.append(dep)

        for p in resolved_profiles:
            file = profile_map[p]["file"]
            if file not in execution_plan:
                execution_plan[file] = []
            execution_plan[file].append(p)

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

    registry = load_registry()
    profile_map = _get_profile_map()

    # 1. Validate requested profiles
    invalid_profiles = [p for p in profiles if p not in profile_map]
    if invalid_profiles:
        console.print(
            f"[bold red]Error:[/bold red] Unknown profiles: {', '.join(invalid_profiles)}"
        )
        raise typer.Exit(1)

    # 2. Dynamically Resolve Dependencies (Recursive Graph Traversal)
    resolved_profiles = set(profiles)
    queue = list(profiles)

    while queue:
        current = queue.pop(0)
        stack_id = profile_map[current]["stack_id"]
        stack = registry.stacks[stack_id]
        for dep in stack.depends_on:
            # Assuming the dependency name in registry maps 1:1 to a profile name here.
            # (e.g. stack "base" depends on "deps", which happens to be the profile "deps")
            if dep not in resolved_profiles:
                resolved_profiles.add(dep)
                queue.append(dep)

    # 3. Group and Order Profiles
    # Enforce a lightweight topological sort: deps always starts 1st, base 2nd, then targets
    order_weights = {"deps": 0, "base": 1}
    sorted_profiles = sorted(
        list(resolved_profiles), key=lambda p: (order_weights.get(p, 99), p)
    )

    execution_plan = {}
    for p in sorted_profiles:
        file = profile_map[p]["file"]
        if file not in execution_plan:
            execution_plan[file] = []
        execution_plan[file].append(p)

    # 4. Print Dry Run
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

    # 5. Execute in Order
    for file, profs in execution_plan.items():
        is_base = "base" in profs or "deps" in profs
        prefix = "🧱 Infrastructure" if is_base else "🚀 Target"

        console.print(
            f"📥 Pulling images for {prefix} ([cyan]{', '.join(profs)}[/cyan])..."
        )
        pull_stack_images(file, profs)

        console.print(f"⚙️ Launching {prefix} ([cyan]{', '.join(profs)}[/cyan])...")
        try:
            launch_stack(file, profs)
        except Exception as e:
            console.print(f"[bold red]Failed to start {file}:[/bold red] {e}")
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

    # Destructive Action Confirmation
    if all and volumes and not dry_run:
        typer.confirm(
            "⚠️ This will destroy ALL profiles and WIPE ALL LOCAL DATA. Are you sure?",
            abort=True,
        )

    profile_map = _get_profile_map()
    registry = load_registry()

    execution_plan = {}

    # 1. Handle "Stop All"
    if all:
        # Reverse iterate stacks to teardown dependents before base
        for stack_id in reversed(list(registry.stacks.keys())):
            stack = registry.stacks[stack_id]
            if stack.profiles:
                execution_plan[stack.file] = stack.profiles
    else:
        # 2. Handle specific profiles
        if not profiles:
            console.print(
                "[bold red]Error:[/bold red] Please specify profile names or use --all"
            )
            raise typer.Exit(1)

        invalid_profiles = [p for p in profiles if p not in profile_map]
        if invalid_profiles:
            console.print(
                f"[bold red]Error:[/bold red] Unknown profiles: {', '.join(invalid_profiles)}"
            )
            raise typer.Exit(1)

        for p in profiles:
            file = profile_map[p]["file"]
            if file not in execution_plan:
                execution_plan[file] = []
            execution_plan[file].append(p)

    # 3. Print Dry Run
    if dry_run:
        console.print(Panel("[bold yellow]Dry Run Teardown Plan[/bold yellow]"))
        for file, profs in execution_plan.items():
            console.print(f"🛑 [cyan]{file}[/cyan]")
            for p in profs:
                console.print(f"  └─ 💥 Stop Profile: [bold red]{p}[/bold red]")
        if volumes:
            console.print("\n[bold red]⚠️ Volumes will be destroyed.[/bold red]")
        return

    # 4. Execute
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
