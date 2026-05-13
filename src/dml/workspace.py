import shutil
from pathlib import Path

from dml.config import INTERNAL_RESOURCES_DIR, get_workspace_dir


def init_workspace(force: bool = False):
    """Copies all internal resources to the local workspace."""
    workspace = get_workspace_dir()

    # Nuke the existing workspace if force is True
    if force and workspace.exists():
        shutil.rmtree(workspace)
        print(f"🗑️  Removed existing workspace at {workspace.relative_to(Path.cwd())}/")

    if not workspace.exists():
        workspace.mkdir(parents=True)
        print(f"📁 Created workspace at {workspace.relative_to(Path.cwd())}/")

    # Iterate over everything in the internal resources
    for item in INTERNAL_RESOURCES_DIR.iterdir():
        dest = workspace / item.name

        # Only copy if it doesn't exist (or was just deleted by force)
        if not dest.exists():
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            print(f"  └─ Copied: {item.name}")
