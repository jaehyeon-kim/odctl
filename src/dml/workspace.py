import shutil
from pathlib import Path
from dml.config import INTERNAL_RESOURCES_DIR, get_workspace_dir


def init_workspace():
    """Copies all internal resources to the local workspace."""
    workspace = get_workspace_dir()

    if not workspace.exists():
        workspace.mkdir(parents=True)
        print(f"📁 Created workspace at {workspace.relative_to(Path.cwd())}/")

    # Iterate over everything in the internal resources
    for item in INTERNAL_RESOURCES_DIR.iterdir():
        dest = workspace / item.name

        # Only copy if it doesn't exist so we don't overwrite user edits
        if not dest.exists():
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            print(f"  └─ Copied: {item.name}")
