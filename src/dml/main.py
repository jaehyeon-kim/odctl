import typer
from rich.console import Console
from rich.table import Table
from dml.registry import load_registry
from dml.docker import is_docker_running, get_stack_ports

app = typer.Typer(
    help="DML CLI: Semantic Orchestrator for DataML Stacks",
    no_args_is_help=True,
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
        table = Table(title="Available DataML Stacks", header_style="bold magenta")

        table.add_column("Stack ID", style="cyan", no_wrap=True)
        table.add_column("Description")
        table.add_column("Profiles", style="green")
        if deep:
            table.add_column("Port Mappings", style="blue")
        table.add_column("Capacities", style="yellow")

        for stack_id, config in registry.stacks.items():
            row = [stack_id, config.description, ", ".join(config.profiles)]

            if deep:
                ports = get_stack_ports(config.file, config.profiles)
                row.append(", ".join(ports) if ports else "N/A")

            row.append(", ".join(config.capacities))
            table.add_row(*row)

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def up(stack_name: str):
    """Launch a stack (Placeholder for Ticket 3)."""
    if not is_docker_running():
        console.print("[bold red]Error:[/bold red] Docker is not reachable.")
        raise typer.Exit(1)
    console.print(f"🚀 Preparing {stack_name}...")


if __name__ == "__main__":
    app()
