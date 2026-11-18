import pytest

from odctl.config import (
    UnreadableFileError,
    get_active_dir,
    get_compose_path,
    get_internal_resources_dir,
    get_registry_path,
    read_yaml,
)


def test_active_dir_fallback_to_internal(mock_workspace, monkeypatch):
    """Should use internal resources if local workspace doesn't exist yet."""
    # Remove the local .odctl workspace created by the fixture
    workspace_dir = mock_workspace / ".odctl"
    if workspace_dir.exists():
        workspace_dir.rmdir()

    # Assert it gracefully falls back to the real internal resources directory
    assert get_active_dir() == get_internal_resources_dir()


def test_active_dir_uses_workspace(mock_workspace):
    """Should prefer local .odctl workspace if it exists."""
    workspace_dir = mock_workspace / ".odctl"
    assert get_active_dir() == workspace_dir


def test_get_registry_path(mock_workspace):
    """Validates registry path updates dynamically based on active directory."""
    expected_path = mock_workspace / ".odctl" / "registry.yml"
    assert get_registry_path() == expected_path


def test_get_compose_path(mock_workspace):
    """Validates file-specific paths generation."""
    expected_path = mock_workspace / ".odctl" / "compose-spark.yml"
    assert get_compose_path("compose-spark.yml") == expected_path


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a:\n  b: 1\n  ports: !reset []\n", {"a": {"b": 1}}),
        ("a: !reset\n  b: 1\nc: 2\n", {"c": 2}),
        ("a:\n  - 1\n  - !reset 2\n  - 3\n", {"a": [1, 3]}),
        ("a: !override\n  - 8080:80\n", {"a": ["8080:80"]}),
        ("a: !override {b: 1}\n", {"a": {"b": 1}}),
        ("a: !override 5\nb: !override '5'\n", {"a": 5, "b": "5"}),
        (
            "x: &x {b: 1}\na: !override\n  <<: *x\n  c: 2\n",
            {"x": {"b": 1}, "a": {"b": 1, "c": 2}},
        ),
    ],
    ids=[
        "reset key",
        "reset mapping",
        "reset item",
        "override list",
        "override map",
        "override scalars",
        "override with merge",
    ],
)
def test_a_file_with_compose_tags_reads_as_compose_reads_it(tmp_path, text, expected):
    """`safe_load` refused `!reset` and `!override`, which Compose accepts
    (compose-go loader/reset.go): it drops a `!reset` node and keeps an
    `!override` node as written."""
    path = tmp_path / "compose-x.yml"
    path.write_text(text)
    assert read_yaml(path, "compose-x.yml") == expected


def test_an_unknown_tag_is_still_not_valid_yaml(tmp_path):
    path = tmp_path / "compose-x.yml"
    path.write_text("a: !foo 1\n")
    with pytest.raises(UnreadableFileError, match="not valid YAML"):
        read_yaml(path, "compose-x.yml")
