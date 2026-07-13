from pathlib import Path
from typing import List, Optional

import typer

from odctl import ui
from odctl.docker import (
    get_managed_containers,
    get_managed_logs,
    get_stack_details,
    is_docker_running,
    launch_stack,
    pull_stack_images,
    restart_managed_containers,
    stop_stack,
)
from odctl.planner import build_execution_plan, get_profile_map
from odctl.registry import load_registry
from odctl.workspace import get_workspace_dir, init_workspace

app = typer.Typer(
    name="odctl",
    help="""
[bold cyan]ODCTL CLI[/bold cyan] - Orchestrator for the Open Data Stack.

Manage your local data engineering and MLOps infrastructure effortlessly.
Provides commands to inspect, provision, and tear down curated Docker Compose stacks.
""",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# View all profiles and exposed ports[/dim]\n
  $ [bold cyan]odctl list -d[/bold cyan]\n\n
  [dim]# See exactly what the airflow profile provisions[/dim]\n
  $ [bold cyan]odctl explain kafka-lite[/bold cyan]\n\n
  [dim]# Launch specific profiles and their dependencies[/dim]\n
  $ [bold cyan]odctl up flink1-lite kafka-lite spark-lite[/bold cyan]\n\n
  [dim]# Complete teardown and wipe all data[/dim]\n
  $ [bold cyan]odctl down --all --volumes[/bold cyan]
""",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable debug-level logging across all commands.",
        rich_help_panel="Global Options",
    ),
    workspace: Path = typer.Option(
        "./.odctl",
        "--workspace",
        "-w",
        help="Path to the ODCTL workspace directory.",
        rich_help_panel="Global Options",
    ),
):
    ctx.obj = {"verbose": verbose, "workspace": workspace}


@app.command(
    name="list",
    rich_help_panel="Inspection & Info",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# View all basic profiles[/dim]\n
  $ [bold cyan]odctl list[/bold cyan]\n\n
  [dim]# View profiles, underlying services, and ports[/dim]\n
  $ [bold cyan]odctl list -d[/bold cyan]
""",
)
@app.command(name="ls", hidden=True)
def list_profiles(
    details: bool = typer.Option(
        False,
        "--details",
        "-d",
        help="Inspect docker-compose files to show exact services and exposed host ports.",
    ),
):
    """
    List all available profiles and their capabilities.

    A [bold]profile[/bold] is a specific capability or technology (e.g., `kafka-lite`, `spark-lite`, `airflow`)
    provided by the Open Data Stack. This command lists them alongside their parent stack.
    """
    try:
        registry = load_registry()
        ui.print_profile_table(registry, details, get_stack_details)
    except Exception as e:
        ui.print_error(str(e))
        raise typer.Exit(1)


@app.command(
    rich_help_panel="Inspection & Info",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# See what the Spark profile provisions[/dim]\n
  $ [bold cyan]odctl explain spark-lite[/bold cyan]
""",
)
def explain(
    profile: str = typer.Argument(
        ..., help="The target profile to inspect (e.g., 'airflow', 'kafka-lite')."
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

    # Extract all 4 values returned by the updated get_stack_details
    services, ports, images, volumes = get_stack_details(stack.file, [profile])

    usage_text = stack.usage
    if isinstance(usage_text, dict):
        usage_text = usage_text.get(
            profile, f"• No specific usage guide for profile: {profile}"
        )

    ui.print_explain_panel(
        profile,
        stack.parent or stack_id,
        stack.file,
        stack.description,
        stack.depends_on or ["None"],
        services,
        ports,
        images,
        volumes,
        stack.role,
        usage_text,
    )


@app.command(
    rich_help_panel="Workspace",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# Initialize a new workspace in ./.odctl/[/dim]\n
  $ [bold cyan]odctl init[/bold cyan]\n\n
  [dim]# Recreate workspace, overwriting any local changes[/dim]\n
  $ [bold cyan]odctl init --force[/bold cyan]
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
    Initialize a local .odctl workspace for custom configurations.

    Copies the bundled docker-compose files, configs, and `.env` template into a
    local `./.odctl/` directory. You can then edit these files directly to customize the stack.
    """
    if force and get_workspace_dir().exists():
        typer.confirm(
            "⚠️  This will wipe out local modifications. Are you sure?", abort=True
        )
    init_workspace(force=force)
    ui.print_success("Workspace initialized! You can now edit any file in ./.odctl/")


@app.command(
    rich_help_panel="Cluster Lifecycle",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# Pre-fetch images for all profiles[/dim]\n
  $ [bold cyan]odctl pull --all[/bold cyan]\n\n
  [dim]# Pre-fetch images just for Flink 1.x and Spark[/dim]\n
  $ [bold cyan]odctl pull flink1-lite kafka-lite[/bold cyan]
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
[bold underline]Examples:[/bold underline]\n
  [dim]# Launch Clickhouse, Flink 1.x, and their dependencies[/dim]\n
  $ [bold cyan]odctl up ch-lite flink1-lite[/bold cyan]\n\n
  [dim]# Preview what would be launched for Airflow[/dim]\n
  $ [bold cyan]odctl up airflow --dry-run[/bold cyan]\n\n
  [dim]# Force pull latest images before launching[/dim]\n
  $ [bold cyan]odctl up kafka-lite --pull[/bold cyan]
""",
)
def up(
    profiles: List[str] = typer.Argument(
        ..., help="One or more profiles to launch (e.g., 'ch-lite', 'kafka-lite')."
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
    Launch Open Data profiles.

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
[bold underline]Examples:[/bold underline]\n
  [dim]# Stop specific profile(s)[/dim]\n
  $ [bold cyan]odctl down kafka-lite[/bold cyan]\n\n
  [dim]# Stop all running profiles[/dim]\n
  $ [bold cyan]odctl down --all[/bold cyan]\n\n
  [dim]# Complete teardown and wipe all data[/dim]\n
  $ [bold cyan]odctl down --all -v[/bold cyan]
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


@app.command(
    name="ps",
    rich_help_panel="Inspection & Info",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# Show all running containers managed by ODCTL[/dim]\n
  $ [bold cyan]odctl ps --all[/bold cyan]\n\n
  [dim]# Show containers just for specific profiles[/dim]\n
  $ [bold cyan]odctl ps kafka-lite spark-lite[/bold cyan]
""",
)
def ps(
    profiles: Optional[List[str]] = typer.Argument(
        None, help="Specific profiles to inspect."
    ),
    all: bool = typer.Option(
        False, "--all", "-a", help="Show all containers managed by ODCTL."
    ),
):
    """
    List Docker containers managed by the Open Data Stack.

    Filters out system containers and only shows those belonging to requested profiles.
    """
    if not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    # Use resolve_deps=False so we ONLY see what was explicitly requested
    plan = build_execution_plan(profiles, all, resolve_deps=False)

    containers = get_managed_containers(plan)
    ui.print_ps_table(containers)


@app.command(name="info", rich_help_panel="Inspection & Info")
def info():
    ui.print_package_info()


@app.command(
    name="logs",
    rich_help_panel="Management",
    epilog="""
[bold underline]Examples:[/bold underline]\n
  [dim]# Tail the last 50 lines of all Flink containers and follow live[/dim]\n
  $ [bold cyan]odctl logs flink1-lite -n 50 -f[/bold cyan]\n\n
  [dim]# View logs strictly for the JobManager service[/dim]\n
  $ [bold cyan]odctl logs flink1-lite -s jobmanager-1[/bold cyan]\n\n
  [dim]# Show logs with timestamps for the last 10 minutes[/dim]\n
  $ [bold cyan]odctl logs kafka-lite --since 10m -t[/bold cyan]
""",
)
def logs(
    profiles: List[str] = typer.Argument(..., help="Profiles to fetch logs for."),
    service: Optional[str] = typer.Option(
        None,
        "--service",
        "-s",
        help="Filter to a specific compose service (Use 'odctl ps' to find names).",
    ),
    follow: bool = typer.Option(
        False, "--follow", "-f", help="Follow log output in real-time."
    ),
    tail: str = typer.Option(
        "all", "--tail", "-n", help="Number of lines to show from the end of the logs."
    ),
    timestamps: bool = typer.Option(
        False, "--timestamps", "-t", help="Show timestamps."
    ),
    since: Optional[str] = typer.Option(
        None, "--since", help="Show logs since timestamp or relative (e.g. '42m')."
    ),
    until: Optional[str] = typer.Option(
        None, "--until", help="Show logs before a timestamp or relative."
    ),
):
    """Fetch the logs of containers managed by specific profiles."""
    if not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    plan = build_execution_plan(profiles, resolve_deps=False)
    get_managed_logs(
        execution_plan=plan,
        follow=follow,
        tail=tail,
        timestamps=timestamps,
        since=since,
        until=until,
        service=service,
    )


@app.command(name="restart", rich_help_panel="Management")
def restart(profiles: List[str] = typer.Argument(..., help="Profiles to restart.")):
    """Restart one or more specific profiles."""
    if not is_docker_running():
        ui.print_error("Docker is not reachable.")
        raise typer.Exit(1)

    plan = build_execution_plan(profiles, resolve_deps=False)
    ui.print_step("Restarting containers...")
    restart_managed_containers(plan)
    ui.print_success("Restart complete.")


if __name__ == "__main__":
    app()
