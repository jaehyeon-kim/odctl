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
        ("a: !override 5\nb: !override '5'\n", {"a": "5", "b": "5"}),
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


@pytest.mark.parametrize(
    "text, expected",
    [
        ("p: 2222:22\n", {"p": "2222:22"}),
        (
            "a: yes\nb: on\nc: off\nd: true\ne: FALSE\n",
            {"a": "yes", "b": "on", "c": "off", "d": True, "e": False},
        ),
        (
            "a: 017\nb: 0x1f\nc: 1_000\nd: 1.5\ne: .inf\n",
            {"a": 15, "b": 31, "c": 1000, "d": 1.5, "e": float("inf")},
        ),
        (
            "x: &x {ports: [80]}\na:\n  <<: *x\n  ports: !reset []\n",
            {"x": {"ports": [80]}, "a": {"ports": [80]}},
        ),
        (
            "a: 0930\nb: 09\nc: 0_8\nd: 0b_\ne: 0X1F\nf: -0\n",
            {"a": 930.0, "b": 9.0, "c": 8.0, "d": "0b_", "e": 31, "f": -0.0},
        ),
        (
            "a: 18446744073709551616\nb: 1e3\nc: 1:30\nd: 2024-01-02\n",
            {
                "a": 1.8446744073709552e19,
                "b": 1000.0,
                "c": "1:30",
                "d": __import__("datetime").date(2024, 1, 2),
            },
        ),
        ("x: {<<: [{k: !reset null, m: 1}, {k: 2}]}\n", {"x": {"k": 2, "m": 1}}),
        (
            "x: {inner: {deeper: &a {k: !reset null, m: 1}}}\nt: {<<: [*a, {k: 3}]}\n",
            {"x": {"inner": {"deeper": {"m": 1}}}, "t": {"k": 3, "m": 1}},
        ),
    ],
    ids=[
        "sexagesimal port",
        "yaml 1.1 booleans",
        "numbers",
        "reset then merge",
        "leading zeros",
        "large and other",
        "reset in a merge source",
        "nested anchor",
    ],
)
def test_read_yaml_reads_plain_values_as_compose_does(tmp_path, text, expected):
    """Compose's go-yaml reads YAML 1.2 values and drops a `!reset` key before merging."""
    path = tmp_path / "compose.yml"
    path.write_text(text)
    assert read_yaml(path, "compose.yml") == expected


def test_read_yaml_gives_go_yaml_number_types(tmp_path):
    """go-yaml reads `-0` and a number past 64 bits as floats, and `017` as an int."""
    path = tmp_path / "compose.yml"
    path.write_text("a: -0\nb: 18446744073709551616\nc: 017\nd: 0930\n")
    data = read_yaml(path, "compose.yml")
    assert [type(data[k]) for k in "abcd"] == [float, float, int, float]
    assert str(data["a"]) == "-0.0" and data["c"] == 15


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a: !!float 5\n", 5.0),
        ("a: !!int 017\n", 15),
        ("a: 1e999\n", "1e999"),
        ("a: .1e999\n", ".1e999"),
        ("a: !!bool TRUE\n", True),
        ("a: !!null ~\n", None),
    ],
    ids=[
        "float tag on an int",
        "int tag",
        "float past the range",
        "dot float past the range",
        "bool tag",
        "null tag",
    ],
)
def test_read_yaml_reads_tagged_and_large_numbers_as_go_yaml(tmp_path, text, expected):
    path = tmp_path / "compose.yml"
    path.write_text(text)
    value = read_yaml(path, "compose.yml")["a"]
    assert (type(value), value) == (type(expected), expected)


@pytest.mark.parametrize(
    "text",
    [
        "a: !!int 0930\n",
        "a: !!int true\n",
        "a: !!float 1e999\n",
        "a: !!float yes\n",
        "a: !!float .1e999\n",
        "a: !!bool yes\n",
        "a: !!bool 1\n",
        "a: !!null abc\n",
    ],
)
def test_read_yaml_refuses_a_number_tag_go_yaml_refuses(tmp_path, text):
    path = tmp_path / "compose.yml"
    path.write_text(text)
    with pytest.raises(UnreadableFileError):
        read_yaml(path, "compose.yml")
