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


def test_every_profile_has_a_section_on_its_stack_page(gen_pages, pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    for stack_id, stack in registry.stacks.items():
        page = pages[f"profiles/{stack_id}.md"]
        for profile in stack.profiles:
            assert f"\n## {profile}\n" in page, f"{profile} missing from {stack_id}.md"
            assert (
                f"[`{profile}`]({stack_id}.md#{profile})" in pages["profiles/index.md"]
            )


def test_every_stack_page_is_in_the_profiles_nav(gen_pages, pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    summary = pages["profiles/SUMMARY.md"]
    for stack_id in registry.stacks:
        assert f"]({stack_id}.md)" in summary


def test_every_stack_is_in_exactly_one_group(gen_pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    grouped = [s for _, stacks in gen_pages.STACK_GROUPS for s in stacks]
    for stack_id in registry.stacks:
        assert grouped.count(stack_id) == 1, (
            f"{stack_id} is in {grouped.count(stack_id)} groups"
        )
    assert set(grouped) <= set(registry.stacks), (
        "a group names a stack not in registry.yml"
    )


def test_profiles_nav_has_one_entry_per_stack(gen_pages, pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    summary = pages["profiles/SUMMARY.md"]
    for group, _ in gen_pages.STACK_GROUPS:
        assert f"\n- {group}\n" in summary
    for stack_id in registry.stacks:
        assert summary.count(f"]({stack_id}.md") == 1
        assert f"[{stack_id}]({stack_id}.md)" in summary
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
