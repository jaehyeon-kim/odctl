from odctl.workspace import get_cli_version, init_workspace


def test_get_cli_version(monkeypatch):
    assert get_cli_version() is not None


def test_init_workspace(tmp_path, monkeypatch):
    # Mock get_workspace_dir to return our tmp_path
    monkeypatch.setattr(
        "odctl.workspace.get_workspace_dir", lambda: tmp_path / ".odctl"
    )

    # Mock INTERNAL_RESOURCES_DIR to point to a temporary internal dir
    internal_dir = tmp_path / "internal"
    internal_dir.mkdir()
    (internal_dir / "test_file.txt").write_text("hello")
    internal_subdir = internal_dir / "subdir"
    internal_subdir.mkdir()
    (internal_subdir / "subfile.txt").write_text("world")

    monkeypatch.setattr("odctl.workspace.INTERNAL_RESOURCES_DIR", internal_dir)

    # Run init_workspace
    init_workspace(force=False)

    # Verify .odctl was created and files were copied
    workspace = tmp_path / ".odctl"
    assert workspace.exists()
    assert (workspace / "test_file.txt").read_text() == "hello"
    assert (workspace / "subdir" / "subfile.txt").read_text() == "world"
    assert (workspace / ".env").exists()

    # Run with force=True
    (workspace / "test_file.txt").write_text("modified")
    init_workspace(force=True)
    assert (workspace / "test_file.txt").read_text() == "hello"


def _workspace_with_tag(tmp_path, monkeypatch, tag):
    workspace = tmp_path / ".odctl"
    workspace.mkdir()
    (workspace / ".env").write_text(f"# generated\nTAG={tag}\n")
    monkeypatch.setattr("odctl.workspace.get_workspace_dir", lambda: workspace)
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "0.8.0")
    monkeypatch.delenv("TAG", raising=False)


def test_stale_workspace_tag_is_reported(tmp_path, monkeypatch):
    from odctl.workspace import stale_workspace_tag

    _workspace_with_tag(tmp_path, monkeypatch, "0.7.0")
    assert stale_workspace_tag() == "0.7.0"


def test_matching_workspace_tag_is_not_reported(tmp_path, monkeypatch):
    from odctl.workspace import stale_workspace_tag

    _workspace_with_tag(tmp_path, monkeypatch, "0.8.0")
    assert stale_workspace_tag() is None


def test_shell_tag_is_an_explicit_choice(tmp_path, monkeypatch):
    from odctl.workspace import stale_workspace_tag

    _workspace_with_tag(tmp_path, monkeypatch, "0.7.0")
    monkeypatch.setenv("TAG", "0.7.0")
    assert stale_workspace_tag() is None


def test_no_workspace_is_not_reported(tmp_path, monkeypatch):
    from odctl.workspace import stale_workspace_tag

    monkeypatch.setattr(
        "odctl.workspace.get_workspace_dir", lambda: tmp_path / ".odctl"
    )
    monkeypatch.delenv("TAG", raising=False)
    assert stale_workspace_tag() is None


def test_stale_workspace_warns_on_every_command_but_init(tmp_path, monkeypatch):
    """An old workspace changes what list shows, not only what up starts."""
    from typer.testing import CliRunner

    from odctl.main import app

    _workspace_with_tag(tmp_path, monkeypatch, "0.7.0")
    runner = CliRunner()

    listed = runner.invoke(app, ["list"])
    assert "TAG=0.7.0" in listed.stdout

    init_help = runner.invoke(app, ["init", "--help"])
    assert "TAG=0.7.0" not in init_help.stdout


def test_tag_defaults_to_the_cli_version_without_a_workspace(tmp_path, monkeypatch):
    """Without a workspace the images used to run as `latest`, and a cached older
    `latest` kept running after an upgrade (#127)."""
    import os

    from odctl.workspace import default_tag_to_cli_version

    monkeypatch.setattr(
        "odctl.workspace.get_workspace_dir", lambda: tmp_path / ".odctl"
    )
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "1.0.1")
    default_tag_to_cli_version()
    assert os.environ["TAG"] == "1.0.1"


def test_tag_is_left_alone_with_a_workspace_or_a_shell_tag(tmp_path, monkeypatch):
    import os

    from odctl.workspace import default_tag_to_cli_version

    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "1.0.1")

    workspace = tmp_path / ".odctl"
    workspace.mkdir()
    monkeypatch.setattr("odctl.workspace.get_workspace_dir", lambda: workspace)
    default_tag_to_cli_version()
    assert "TAG" not in os.environ, "the workspace's .env decides the tag"

    monkeypatch.setattr("odctl.workspace.get_workspace_dir", lambda: tmp_path / "none")
    monkeypatch.setenv("TAG", "0.10.0")
    default_tag_to_cli_version()
    assert os.environ["TAG"] == "0.10.0"


def test_cli_commands_resolve_the_cli_version_without_a_workspace(
    tmp_path, monkeypatch
):
    """The tag odctl checks before starting is the one compose will use."""
    from typer.testing import CliRunner

    from odctl.docker import resolve_image_tag
    from odctl.main import app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("odctl.workspace.get_cli_version", lambda: "1.0.1")
    CliRunner().invoke(app, ["list"])
    assert resolve_image_tag() == "1.0.1"
