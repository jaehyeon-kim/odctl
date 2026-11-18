import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from importlib.metadata import PackageNotFoundError, version

from odctl.config import INTERNAL_RESOURCES_DIR, get_workspace_dir, read_env_file


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
    if workspace.exists() and read_env_file(workspace / ".env").get("TAG"):
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
    tag = read_env_file(get_workspace_dir() / ".env").get("TAG")
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


# The keys `odctl init` writes to `.odctl/.env`, in the order it writes them: each group
# is followed by a blank line, and each key has its comment lines and its value; None is
# the CLI version. `scripts/gen_pages.py` reads the keys from here for the docs.
ENV_FILE: Tuple[Tuple[Tuple[Tuple[str, ...], str, Optional[str]], ...], ...] = (
    (((), "TAG", None), ((), "TZ", "UTC")),
    (
        (
            ("Airflow Additional Dependencies", '_AIRFLOW_PIP_DEPS="scikit-learn"'),
            "_AIRFLOW_PIP_DEPS",
            '""',
        ),
    ),
    (
        (
            ("MLOps Additional Dependencies", '_MLOPS_PIP_DEPS="pyod river"'),
            "_MLOPS_PIP_DEPS",
            '""',
        ),
    ),
    (
        (
            (
                "Airflow lineage: where Airflow sends OpenLineage events. Empty",
                "means Airflow sends none. Marquez is the lineage profile.",
                "AIRFLOW_OPENLINEAGE_TRANSPORT='"
                '{"type": "http", "url": "http://marquez-api:5000"}\'',
            ),
            "AIRFLOW_OPENLINEAGE_TRANSPORT",
            '""',
        ),
    ),
    (
        (
            (
                "OpenMetadata Ingestion Additional Dependencies",
                '_METADATA_PIP_DEPS="faker"',
            ),
            "_METADATA_PIP_DEPS",
            '""',
        ),
    ),
    (
        (
            (
                "OpenMetadata AutoPilot",
                "When a service is added in the OpenMetadata UI, AutoPilot creates",
                "and runs default agents for it. It is off unless this is true.",
                'METADATA_AUTOPILOT="true"',
            ),
            "METADATA_AUTOPILOT",
            '"false"',
        ),
    ),
    # Left empty on purpose. mlflow-serve has nothing to serve until a model is
    # logged, so an empty value keeps it waiting idle instead of serving something
    # unintended.
    (
        (
            (
                "MLflow Model Server target: models:/<name>@<alias>,",
                "runs:/<run-id>/<artifact-path>, or an s3:// path",
                'MODEL_URI="models:/my-model@champion"',
            ),
            "MODEL_URI",
            '""',
        ),
    ),
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

    # registry.yml goes first: it is what marks a folder as a workspace, so a copy
    # that fails part way leaves a folder that `init` and `init --force` still take.
    items = sorted(
        INTERNAL_RESOURCES_DIR.iterdir(), key=lambda i: i.name != "registry.yml"
    )
    for item in items:
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
        groups = [
            "".join(
                "".join(f"# {line}\n" for line in comments)
                + f"{key}={cli_version if value is None else value}\n"
                for comments, key, value in group
            )
            for group in ENV_FILE
        ]
        with open(env_file, "w") as f:
            f.write(f"# Auto-generated by Open Data Stack CLI v{cli_version}\n")
            f.write("\n".join(groups))

        print(f"  └─ Generated: .env (TAG={cli_version})")
