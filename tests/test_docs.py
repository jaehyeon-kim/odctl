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
    return [tech for _, _, techs in gen_pages.TECH_GROUPS for tech in techs]


def test_every_profile_is_on_exactly_one_page(gen_pages):
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    placed = [p for _, profiles in _techs(gen_pages) for p in profiles]
    for stack in registry.stacks.values():
        for profile in stack.profiles:
            assert placed.count(profile) == 1, (
                f"{profile} is on {placed.count(profile)} pages"
            )
    known = {p for stack in registry.stacks.values() for p in stack.profiles}
    assert set(placed) <= known, "a page names a profile not in registry.yml"


def test_every_profile_has_a_section_and_an_index_row(gen_pages, pages):
    for group, _, techs in gen_pages.TECH_GROUPS:
        path = f"{gen_pages._slug(group)}.md"
        page = pages[f"profiles/{path}"]
        for title, profiles in techs:
            assert f"\n## {title}\n" in page, f"{title} missing from {path}"
            for profile in profiles:
                assert f"\n### {profile}\n" in page, f"{profile} missing from {path}"
                assert f"[`{profile}`]({path}#{profile})" in pages["profiles/index.md"]


def test_profiles_nav_has_one_entry_per_area(gen_pages, pages):
    summary = pages["profiles/SUMMARY.md"]
    for group, _, _ in gen_pages.TECH_GROUPS:
        assert f"\n- [{group}]({gen_pages._slug(group)}.md)\n" in summary
    assert len(summary.strip().splitlines()) == len(gen_pages.TECH_GROUPS) + 1
    assert "#" not in summary


def test_version_tags_are_shown_as_the_cli_version(pages):
    text = "".join(pages.values())
    assert "${TAG" not in text
    assert (
        "`ghcr.io/jaehyeon-kim/odctl/deps:<CLI version>`"
        in pages["profiles/storage-and-catalog.md"]
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


def test_local_addresses_become_nofollow_links():
    hook = _load("local_links", REPO / "scripts" / "local_links.py")
    html = (
        "<p>Open <code>http://127.0.0.1:8123/play</code> or "
        "<code>kafka:19092</code>.</p>"
        "<pre><code>http://127.0.0.1:8123</code></pre>"
    )
    out = hook.link_local_addresses(html)
    assert (
        '<a href="http://127.0.0.1:8123/play" rel="nofollow">'
        "<code>http://127.0.0.1:8123/play</code></a>" in out
    )
    assert "<code>kafka:19092</code>" in out
    assert "<pre><code>http://127.0.0.1:8123</code></pre>" in out


def test_home_page_table_comes_from_the_area_list(gen_pages):
    """The home page holds the marker, and the table built for it has one row per
    area linking that area's profile page, so the two can never disagree."""
    home = (REPO / "docs" / "index.md").read_text()
    assert gen_pages.AREAS_MARKER in home
    assert "| Area | Technologies |" not in home, "the table is written by hand again"
    table = gen_pages.areas_table()
    for group, summary, _ in gen_pages.TECH_GROUPS:
        assert (
            f"| [{group}](profiles/{gen_pages._slug(group)}.md) | {summary} |" in table
        )


def test_readme_diagram_names_every_technology(gen_pages):
    """The README diagram is drawn by hand, so a profile added to the area list
    has to be added to it too. Each technology counts as shown when the diagram
    names it, one of its profiles, or a part of the image in its brackets."""
    import re

    import html

    drawio = (REPO / "image" / "diagram.drawio").read_text()
    labels = " ".join(html.unescape(v) for v in re.findall(r'value="([^"]*)"', drawio))
    text = re.sub(r"<[^>]+>", " ", labels).lower()
    for title, profiles in _techs(gen_pages):
        name = re.sub(r"^apache ", "", re.sub(r"\s*\(.*\)", "", title.lower()))
        bracket = re.search(r"\((.*)\)", title.lower())
        candidates = [name.split()[0], *profiles]
        if bracket:
            candidates += bracket.group(1).split("/")
        assert any(
            re.search(rf"(?<![a-z0-9-]){re.escape(c)}(?![a-z0-9-])", text)
            for c in candidates
        ), f"{title} is not in image/diagram.drawio"


def test_client_versions_in_guides_match_the_stack():
    """The guides tell readers which client version to install, because it has to
    match the server. Renovate updates the compose files and Dockerfiles but not
    the guides, so each version written in a guide is checked against its source."""
    import re

    res = INTERNAL_RESOURCES_DIR
    guides = REPO / "docs" / "guides"

    def one(pattern, text, where):
        found = set(re.findall(pattern, text))
        assert len(found) == 1, f"{where}: expected one version, found {found}"
        return found.pop()

    evidently = one(
        r"evidently/evidently-service:([\d.]+)",
        (res / "compose-mlops.yml").read_text(),
        "compose-mlops.yml",
    )
    feast = one(
        r"feastdev/feature-server:([\d.]+)",
        (res / "compose-mlops.yml").read_text(),
        "compose-mlops.yml",
    )
    dockerfile = (res / "docker" / "mlflow" / "Dockerfile").read_text()
    mlflow = one(r"mlflow/mlflow:v([\d.]+)", dockerfile, "mlflow Dockerfile")
    xgboost = ".".join(
        one(r"xgboost~=([\d.]+)", dockerfile, "mlflow Dockerfile").split(".")[:2]
    )

    text = (guides / "evidently-reports.md").read_text()
    assert set(re.findall(r"evidently==([\d.]+)", text)) == {evidently}
    assert set(re.findall(r"Evidently (\d[\d.]*)", text)) == {evidently}
    text = (guides / "feast-iceberg.md").read_text()
    assert set(re.findall(r"feast\[[^\]]*\]==([\d.]+)", text)) == {feast}
    text = (guides / "mlflow.md").read_text()
    assert set(re.findall(r"MLflow (\d[\d.]*)", text)) == {mlflow}
    assert set(re.findall(r"XGBoost (\d[\d.]*)", text)) == {xgboost}
