"""The plugin manifests and MCP files for Claude Code, Codex and Antigravity."""

import json
import re
import struct

import pytest

from odctl.main import app

from docs_helpers import REPO, load

MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".antigravity-plugin/plugin.json",
]
MARKETPLACES = [
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
]
# Where each tool reads the MCP entry: Claude Code and Codex inline in their
# plugin.json, Antigravity from its own file at the plugin root.
MCP_ENTRIES = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "mcp_config.json",
]


@pytest.fixture(scope="module")
def gen_pages():
    return load("gen_pages", REPO / "scripts" / "gen_pages.py")


def _json(path: str):
    return json.loads((REPO / path).read_text())


def _png_size(path: str):
    header = (REPO / path).read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", header[16:24])


def test_committed_plugin_files_are_generated(gen_pages):
    """Every manifest carries pyproject.toml's version and no file is edited by hand."""
    for path, content in gen_pages.plugin_files().items():
        assert (REPO / path).read_text() == content, (
            f"{path} is out of date; run uv run python scripts/gen_pages.py"
        )


def test_the_version_comes_from_pyproject_into_every_manifest(gen_pages):
    assert re.fullmatch(r"\d+\.\d+\.\d+", gen_pages.package_version())
    files = gen_pages.plugin_files("9.8.7")
    for path in MANIFESTS:
        assert json.loads(files[path])["version"] == "9.8.7", path
    # A marketplace entry with its own version would differ from the manifest's
    # and make Claude Code's validate report a mismatch.
    for path in MARKETPLACES:
        document = json.loads(files[path])
        assert all("version" not in plugin for plugin in document["plugins"]), path


def test_every_tool_reads_the_same_read_only_mcp_entry(gen_pages):
    """The args name a registered command and not `--allow-changes`, which serves `up`
    and `down`. A root `.mcp.json` would also be the repository's own project MCP
    file, which every Claude Code session in odctl loads, so there is none."""
    entry = {"odctl": {"command": "odctl", "args": ["mcp"]}}
    for path in MCP_ENTRIES:
        assert _json(path)["mcpServers"] == entry, path
    assert set(gen_pages.PLUGIN_MCP_FILES) == {"mcp_config.json"}
    assert not (REPO / ".mcp.json").exists()
    names = {
        command.name or command.callback.__name__ for command in app.registered_commands
    }
    assert "mcp" in names


def test_every_manifest_names_the_plugin_odctl():
    for path in MANIFESTS + MARKETPLACES:
        assert _json(path)["name"] == "odctl", path
    for path in MARKETPLACES:
        assert [plugin["name"] for plugin in _json(path)["plugins"]] == ["odctl"], path


def test_every_marketplace_entry_points_at_the_repository_root():
    """Codex needs plugin.json inside the plugin folder, so the folder is
    the repository root."""
    for path in MARKETPLACES:
        assert [plugin["source"] for plugin in _json(path)["plugins"]] == ["./"], path


def test_the_plugin_root_has_the_skill_each_tool_loads():
    skill = REPO / "skills" / "odctl" / "SKILL.md"
    assert skill.is_file()
    assert re.search(r"^name: odctl$", skill.read_text(), re.M)


def test_the_logo_is_a_square_png_of_512_px_or_more_outside_a_dot_folder():
    logos = {
        ".claude-plugin/plugin.json": _json(".claude-plugin/plugin.json")["icon"],
        ".codex-plugin/plugin.json": _json(".codex-plugin/plugin.json")["interface"][
            "logo"
        ],
        ".antigravity-plugin/plugin.json": _json(".antigravity-plugin/plugin.json")[
            "logo"
        ],
    }
    for path, logo in logos.items():
        # Codex needs `./` in front; agy reads a path from the root.
        relative = logo.removeprefix("./")
        assert relative == "docs/assets/logo.png", path
        assert not any(part.startswith(".") for part in relative.split("/")), path
        width, height = _png_size(relative)
        assert width == height >= 512, path
    assert logos[".codex-plugin/plugin.json"].startswith("./")
