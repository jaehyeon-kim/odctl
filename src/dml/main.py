from typing import List, Optional

import typer

from dml import ui  # Import your new UI module
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
  $ [cyan]dml up clickhouse flink1[/cyan]
  $ [cyan]dml down --all --volumes[/cyan]
""",
)


@app.callback()
def main():
    """Orchestrator for the Open DataML Stack."""
    pass


@app.command(name="list")
def list_profiles(
    deep: bool = typer.Option(False, "--deep", "-d", help="Show port mappings"),
):
    """List all available profiles and their capabilities."""
    try:
        registry = load_registry()
        ui.print_profile_table(registry, deep, get_stack_details)
    except Exception as e:
        ui.print_error(str(e))
        raise typer.Exit(1)


@app.command()
def explain(profile: str = typer.Argument(..., help="The profile to inspect")):
    """Explain the details, services, images, and dependencies of a specific profile."""
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


@app.command()
def init(force: bool = typer.Option(False, "--force", "-f", help="Recreate workspace")):
    """Initialize a local .dml workspace for custom configurations."""
    if force and get_workspace_dir().exists():
        typer.confirm(
            "⚠️  This will wipe out local modifications. Are you sure?", abort=True
        )
    init_workspace(force=force)
    ui.print_success("Workspace initialized! You can now edit any file in ./.dml/")


@app.command()
def pull(
    profiles: Optional[List[str]] = typer.Argument(None),
    all: bool = typer.Option(False, "--all"),
):
    """Pre-fetch Docker images without starting the containers."""
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


@app.command()
def up(
    profiles: List[str] = typer.Argument(...),
    dry_run: bool = typer.Option(False, "--dry-run"),
    pull: bool = typer.Option(
        False, "--pull", help="Force pull latest images from registry before starting"
    ),
):
    """Launch DataML profiles."""
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

        # ONLY pull if the user explicitly asks for it!
        if pull:
            ui.print_info(
                f"📥 Pulling images for {prefix} ([cyan]{', '.join(profs)}[/cyan])..."
            )
            pull_stack_images(file, profs)

        ui.print_info(f"⚙️  Launching {prefix} ([cyan]{', '.join(profs)}[/cyan])...")
        try:
            # If the image is missing entirely, Docker Compose will still
            # natively pull it here (pull_policy: missing)
            launch_stack(file, profs)
        except Exception as e:
            ui.print_error(f"Failed to start {file}", details=str(e), show_tip=True)
            raise typer.Exit(1)

    ui.print_success("All requested profiles successfully started!")


@app.command()
def down(
    profiles: Optional[List[str]] = typer.Argument(None),
    all: bool = typer.Option(False, "--all"),
    volumes: bool = typer.Option(False, "--volumes", "-v"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Stop and remove profile containers and networks."""
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
