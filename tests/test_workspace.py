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
