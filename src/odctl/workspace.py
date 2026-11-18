import os
import shutil
from pathlib import Path
from typing import Optional
from importlib.metadata import PackageNotFoundError, version

from odctl.config import INTERNAL_RESOURCES_DIR, get_workspace_dir
from odctl.docker import _read_env_file


def get_cli_version() -> str:
    """
    Retrieve the version of the installed odctl package.

    Returns:
        str: The installed package version, or 'latest' if run directly from source
        without installation.
    """
    try:
        # This string must exactly match the 'name' in your pyproject.toml
        return version("odctl")
    except PackageNotFoundError:
        # Fallback for when you are developing locally and haven't installed the package
        return "latest"


def default_tag_to_cli_version() -> None:
    """
    Run this CLI version's images when no workspace sets TAG.

    The compose files tag odctl's own images `${TAG:-latest}`. Without a
    workspace there is no `.env` to set TAG, so the images ran as `latest`, and
    Docker does not pull an image it already has: after an upgrade an older
    `latest` kept running (#127). A workspace whose `.env` has no TAG, or an empty
    one, ran `latest` the same way. Setting TAG here, as `odctl init` writes it,
    reaches both Docker Compose, which inherits the environment, and
    `resolve_image_tag`. A TAG already set in the shell is left alone, and so is a
    non-empty TAG in the workspace `.env`, read as Compose reads it.
    """
    if "TAG" in os.environ:
        return
    workspace = get_workspace_dir()
    if workspace.exists() and _read_env_file(workspace / ".env").get("TAG"):
        return
    os.environ["TAG"] = get_cli_version()


def stale_workspace_tag() -> Optional[str]:
    """
    Return the workspace's TAG when it no longer matches this CLI's version.

    `odctl init` writes TAG from the CLI version once, so upgrading the CLI later
    leaves the workspace starting the old images and compose files, with no sign
    of it. A TAG set in the shell is an explicit choice and is not reported.

    The workspace's TAG is read as Compose reads `.env`, by the same parser as
    `resolve_image_tag`, so the warning names the tag Compose runs.

    Returns:
        Optional[str]: The stale TAG, or None when there is no workspace, no TAG,
        a shell override, or a match.
    """
    if os.environ.get("TAG"):
        return None
    tag = _read_env_file(get_workspace_dir() / ".env").get("TAG")
    cli = get_cli_version()
    return tag if tag and cli != "latest" and tag != cli else None


def check_workspace_path(workspace: Path) -> None:
    """
    Refuse a workspace path that `odctl init` must not write into or remove.

    `init --force` removes the workspace folder with every file in it, so a folder
    that holds files but no `registry.yml`, which every workspace has, is not taken
    for one. An empty folder, or one that does not exist yet, is a new workspace.

    Args:
        workspace (Path): The workspace folder, from `--workspace` or `./.odctl`.

    Raises:
        ValueError: If the path is a file, or a folder that is not empty and holds no
            `registry.yml`.
    """
    if workspace.is_file():
        raise ValueError(f"{workspace} is a file. Name a folder for the workspace.")
    if (
        workspace.is_dir()
        and any(workspace.iterdir())
        and not (workspace / "registry.yml").exists()
    ):
        raise ValueError(
            f"{workspace} is not an odctl workspace: it holds files and no "
            "registry.yml. Name a new or empty folder, or an existing workspace."
        )


def init_workspace(force: bool = False):
    """
    Copy all internal resources to the local user workspace.

    Args:
        force (bool, optional): If True, completely deletes the existing workspace and
                                recreates it from scratch. Defaults to False.

    Raises:
        ValueError: If the workspace path is a file, or a folder that is not a
            workspace (`check_workspace_path`).
    """
    workspace = get_workspace_dir()
    check_workspace_path(workspace)

    # Nuke the existing workspace if force is True
    if force and workspace.exists():
        shutil.rmtree(workspace)
        print(f"🗑️  Removed existing workspace at {workspace}/")

    if not workspace.exists():
        workspace.mkdir(parents=True)
        print(f"📁 Created workspace at {workspace}/")

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

    # Generate the .env file dynamically
    cli_version = get_cli_version()
    env_file = workspace / ".env"

    # Only create/overwrite .env if force is True OR it doesn't exist yet
    if force or not env_file.exists():
        with open(env_file, "w") as f:
            f.write(f"# Auto-generated by Open Data Stack CLI v{cli_version}\n")
            f.write(f"TAG={cli_version}\n")
            f.write("TZ=UTC\n\n")

            f.write("# Airflow Additional Dependencies\n")
            f.write('# _AIRFLOW_PIP_DEPS="scikit-learn"\n')
            f.write('_AIRFLOW_PIP_DEPS=""\n\n')

            f.write("# MLOps Additional Dependencies\n")
            f.write('# _MLOPS_PIP_DEPS="pyod river"\n')
            f.write('_MLOPS_PIP_DEPS=""\n\n')

            f.write(
                "# Airflow lineage: where Airflow sends OpenLineage events. Empty\n"
            )
            f.write("# means Airflow sends none. Marquez is the lineage profile.\n")
            f.write(
                "# AIRFLOW_OPENLINEAGE_TRANSPORT='"
                '{"type": "http", "url": "http://marquez-api:5000"}\'\n'
            )
            f.write('AIRFLOW_OPENLINEAGE_TRANSPORT=""\n\n')

            f.write("# OpenMetadata Ingestion Additional Dependencies\n")
            f.write('# _METADATA_PIP_DEPS="faker"\n')
            f.write('_METADATA_PIP_DEPS=""\n\n')

            f.write("# OpenMetadata AutoPilot\n")
            f.write(
                "# When a service is added in the OpenMetadata UI, AutoPilot creates\n"
            )
            f.write(
                "# and runs default agents for it. It is off unless this is true.\n"
            )
            f.write('# METADATA_AUTOPILOT="true"\n')
            f.write('METADATA_AUTOPILOT="false"\n\n')

            # Left empty on purpose. mlflow-serve has nothing to serve until a
            # model is logged, so an empty value keeps it waiting idle instead
            # of serving something unintended.
            f.write("# MLflow Model Server target: models:/<name>@<alias>,\n")
            f.write("# runs:/<run-id>/<artifact-path>, or an s3:// path\n")
            f.write('# MODEL_URI="models:/my-model@champion"\n')
            f.write('MODEL_URI=""\n')

        print(f"  └─ Generated: .env (TAG={cli_version})")
