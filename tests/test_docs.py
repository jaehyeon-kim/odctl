"""The generated documentation pages cover every profile and every command."""

import importlib.util
from pathlib import Path

import pytest

from odctl.config import INTERNAL_RESOURCES_DIR
from odctl.main import app

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen_pages():
    return _load("gen_pages", REPO / "scripts" / "gen_pages.py")


@pytest.fixture(scope="module")
def pages(gen_pages):
    return gen_pages.profile_pages(INTERNAL_RESOURCES_DIR)


def _techs(gen_pages):
    return [tech for _, techs in gen_pages.TECH_GROUPS for tech in techs]


def test_every_profile_is_on_exactly_one_page(gen_pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    placed = [p for _, _, profiles in _techs(gen_pages) for p in profiles]
    for stack in registry.stacks.values():
        for profile in stack.profiles:
            assert placed.count(profile) == 1, (
                f"{profile} is on {placed.count(profile)} pages"
            )
    known = {p for stack in registry.stacks.values() for p in stack.profiles}
    assert set(placed) <= known, "a page names a profile not in registry.yml"


def test_every_profile_has_a_section_and_an_index_row(gen_pages, pages):
    for slug, _, profiles in _techs(gen_pages):
        page = pages[f"profiles/{slug}.md"]
        for profile in profiles:
            assert f"\n## {profile}\n" in page, f"{profile} missing from {slug}.md"
            assert f"[`{profile}`]({slug}.md#{profile})" in pages["profiles/index.md"]


def test_profiles_nav_has_one_entry_per_technology(gen_pages, pages):
    summary = pages["profiles/SUMMARY.md"]
    for group, _ in gen_pages.TECH_GROUPS:
        assert f"\n- {group}\n" in summary
    for slug, title, _ in _techs(gen_pages):
        assert summary.count(f"]({slug}.md") == 1
        assert f"[{title}]({slug}.md)" in summary
    assert "#" not in summary


def test_version_tags_are_shown_as_the_cli_version(pages):
    text = "".join(pages.values())
    assert "${TAG" not in text
    assert (
        "`ghcr.io/jaehyeon-kim/odctl/deps:<CLI version>`" in pages["profiles/deps.md"]
    )


def test_cli_reference_covers_every_visible_command(gen_pages):
    reference = gen_pages.cli_reference()
    visible = [
        command.name or command.callback.__name__
        for command in app.registered_commands
        if not command.hidden
    ]
    assert visible, "no commands found on the Typer app"
    for name in visible:
        assert f"\n## odctl {name}\n" in reference
        assert f"Usage: odctl {name} " in reference
    # Hidden aliases stay out, as they do in `odctl --help`.
    assert "## odctl ls\n" not in reference
    # Help is captured as plain text, so no terminal colour codes reach the page.
    assert "\x1b" not in reference
    assert "[bold" not in reference


def test_docs_only_changes_select_no_e2e_groups():
    selector = _load(
        "select_profiles", REPO / ".github" / "scripts" / "select-profiles.py"
    )
    registry = INTERNAL_RESOURCES_DIR / "registry.yml"
    changed = [
        "docs/index.md",
        "docs/guides/telemetry.md",
        "mkdocs.yml",
        "scripts/gen_pages.py",
        "README.md",
    ]
    assert selector.select(changed, registry) == []
