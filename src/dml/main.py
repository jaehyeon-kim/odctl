from typing import List, Optional

import typer

from dml import ui
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
    name="dml",
    help="""
[bold cyan]DML CLI[/bold cyan] - Orchestrator for the Open DataML Stack.

Manage your local data engineering and MLOps infrastructure effortlessly. 
Provides commands to inspect, provision, and tear down curated Docker Compose stacks.
""",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog="""
[bold]Examples:[/bold]\n
  $ [cyan]dml list --deep[/cyan]                     # View all profiles and exposed ports\n
  $ [cyan]dml explain kafka[/cyan]                   # See exactly what the airflow profile provisions\n
  $ [cyan]dml up flink1 kafka spark[/cyan]           # Launch specific profiles and their dependencies\n
  $ [cyan]dml down --all --volumes[/cyan]            # Complete teardown and wipe all data\n
""",
)


@app.callback()
def main():
    pass


@app.command(
    name="list",
    rich_help_panel="Inspection & Info",
    epilog="""
[bold]Examples:[/bold]\n
  $ [cyan]dml list[/cyan]                  # View all basic profiles\n
  $ [cyan]dml list --deep[/cyan]           # View profiles, underlying services, and ports
""",
)
def list_profiles(
    deep: bool = typer.Option(
        False,
        "--deep",
        "-d",
        help="Inspect docker-compose files to show exact services and exposed host ports.",
    ),
):
    """
    List all available profiles and their capabilities.

    A [bold]profile[/bold] is a specific capability or technology (e.g., `kafka`, `spark`, `airflow`)
    provided by the Open DataML Stack. This command lists them alongside their parent stack.
    """
    try:
        registry = load_registry()
        ui.print_profile_table(registry, deep, get_stack_details)
    except Exception as e:
        ui.print_error(str(e))
        raise typer.Exit(1)


@app.command(
    rich_help_panel="Inspection & Info",
    epilog="""
[bold]Examples:[/bold]\n
$ [cyan]dml explain spark[/cyan]           # See what the Spark profile provisions
""",
)
def explain(
    profile: str = typer.Argument(
        ..., help="The target profile to inspect (e.g., 'airflow', 'kafka')."
    ),
):
    """
    Explain the details, services, images, and dependencies of a profile.

    Displays a detailed breakdown of what a profile provisions, its container images,
    exposed host ports, and any prerequisite profiles it depends on.
    """
    registry = load_registry()
    profile_map = get_profile_map()

    if profile not in profile_map:
        ui.print_error(f"Profile '{profile}' not found in registry.")
        raise typer.Exit(1)

    stack_id = profile_map[profile]["stack_id"]
    stack = registry.stacks[stack_id]
    services, ports, images = get_stack_details(stack.file, [profile])

    ui.print_explain_panel(
        profile,
        stack_id,
        stack.file,
        stack.description,
        stack.depends_on or ["None"],
        services,
        ports,
        images,
    )


@app.command(
    rich_help_panel="Workspace",
    epilog="""
[bold]Examples:[/bold]\n
$ [cyan]dml init[/cyan]                    # Initialize a new workspace in ./.dml/\n
$ [cyan]dml init --force[/cyan]            # Recreate workspace, overwriting any local changes
""",
)
def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Wipe out the existing workspace and recreate it from scratch.",
    ),
):
    """
    Initialize a local .dml workspace for custom configurations.

    Copies the bundled docker-compose files, configs, and `.env` template into a
    local `./.dml/` directory. You can then edit these files directly to customize the stack.
    """
    if force and get_workspace_dir().exists():
        typer.confirm(
            "⚠️  This will wipe out local modifications. Are you sure?", abort=True
        )
    init_workspace(force=force)
    ui.print_success("Workspace initialized! You can now edit any file in ./.dml/")


@app.command(
    rich_help_panel="Cluster Lifecycle",
    epilog="""
[bold]Examples:[/bold]\n
$ [cyan]dml pull --all[/cyan]                   # Pre-fetch images for all profiles\n
$ [cyan]dml pull flink1 kafka[/cyan]            # Pre-fetch images just for Flink 1.x and Spark
""",
)
def pull(
    profiles: Optional[List[str]] = typer.Argument(
        None, help="Specific profiles to pull images for."
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Pull images for ALL available profiles in the registry.",
    ),
):
    """
    Pre-fetch Docker images without starting the containers.

    Useful for downloading heavy images (like Spark, Flink, Kafka) ahead of time
    or ensuring you have the latest versions before launching.
    """
    if not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    execution_plan = build_execution_plan(profiles, all, resolve_deps=True)
    ui.print_info("📥 Pre-fetching Docker images...")

    for file, profs in execution_plan.items():
        ui.print_info(f"Fetching images for [yellow]{file}[/yellow]...", style="white")
        try:
            pull_stack_images(file, profs)
        except Exception as e:
            ui.print_error(f"Failed to pull images for {file}", details=str(e))
            raise typer.Exit(1)
    ui.print_success("All images pulled successfully!")


@app.command(
    rich_help_panel="Cluster Lifecycle",
    epilog="""
[bold]Examples:[/bold]\n
$ [cyan]dml up clickhouse flink1[/cyan]            # Launch Clickhouse, Flink 1.x, and their dependencies\n
$ [cyan]dml up airflow --dry-run[/cyan]            # Preview what would be launched for Airflow\n
$ [cyan]dml up kafka --pull[/cyan]                 # Force pull latest images before launching
""",
)
def up(
    profiles: List[str] = typer.Argument(
        ..., help="One or more profiles to launch (e.g., 'clickhouse', 'kafka')."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview the execution plan without actually starting anything.",
    ),
    pull: bool = typer.Option(
        False,
        "--pull",
        help="Force pull the latest images from the registry before starting.",
    ),
):
    """
    Launch DataML profiles.

    Resolves dependencies for the requested profiles and brings up the required
    Docker Compose stacks in the correct topological order.
    """
    if not dry_run and not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    plan = build_execution_plan(profiles, resolve_deps=True)
    if dry_run:
        ui.print_dry_run(plan)
        return

    for file, profs in plan.items():
        is_base = any(x in profs for x in ["base", "deps"])
        prefix = "🧱 Infrastructure" if is_base else "🚀 Target"

        if pull:
            ui.print_info(
                f"📥 Pulling images for {prefix} ([cyan]{', '.join(profs)}[/cyan])..."
            )
            pull_stack_images(file, profs)

        ui.print_info(f"⚙️  Launching {prefix} ([cyan]{', '.join(profs)}[/cyan])...")
        try:
            launch_stack(file, profs)
        except Exception as e:
            ui.print_error(f"Failed to start {file}", details=str(e), show_tip=True)
            raise typer.Exit(1)

    ui.print_success("All requested profiles successfully started!")


@app.command(
    rich_help_panel="Cluster Lifecycle",
    epilog="""
[bold]Examples:[/bold]\n
$ [cyan]dml down kafka[/cyan]                  # Stop specific profile(s)\n
$ [cyan]dml down --all[/cyan]                  # Stop all running profiles\n
$ [cyan]dml down --all -v[/cyan]               # Complete teardown and wipe all data\n
""",
)
def down(
    profiles: Optional[List[str]] = typer.Argument(
        None, help="Specific profiles to stop."
    ),
    all: bool = typer.Option(False, "--all", "-a", help="Stop ALL running profiles."),
    volumes: bool = typer.Option(
        False,
        "--volumes",
        "-v",
        help="Remove named volumes (⚠️ Destroys database/storage data!).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview the teardown plan without actually stopping anything.",
    ),
):
    """
    Stop and remove profile containers and networks.

    Tears down the requested profiles. By default, data volumes are preserved.
    Use [bold red]--volumes[/bold red] to completely wipe the data.
    """
    if not dry_run and not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    if all and volumes and not dry_run:
        typer.confirm(
            "⚠️  This will destroy ALL profiles and WIPE ALL DATA. Are you sure?",
            abort=True,
        )

    plan = build_execution_plan(profiles, all, resolve_deps=False)
    plan = dict(reversed(list(plan.items())))

    if dry_run:
        ui.print_dry_run(plan, is_teardown=True)
        return

    for file, profs in plan.items():
        ui.print_info(f"🛑 Stopping [cyan]{', '.join(profs)}[/cyan]...")
        try:
            stop_stack(file, profs, remove_volumes=volumes)
        except Exception as e:
            ui.print_error(f"Failed to stop {file}", details=str(e))
            raise typer.Exit(1)
    ui.print_success("Teardown complete.")


if __name__ == "__main__":
    app()
