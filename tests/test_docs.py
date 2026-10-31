"""The generated documentation pages cover every profile and every command."""

import re

import pytest

from odctl.config import INTERNAL_RESOURCES_DIR
from odctl.main import app

from docs_helpers import FENCE, REPO, TAUGHT_PAGES, TITLE, load, section


@pytest.fixture(scope="module")
def gen_pages():
    return load("gen_pages", REPO / "scripts" / "gen_pages.py")


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
    selector = load(
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
    hook = load("local_links", REPO / "scripts" / "local_links.py")
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


# Area names in TECH_GROUPS also name a page, its URL and a home table row, so a
# long one stays and wraps in the sidebar.
_LONG_TITLES = {"Stream and Batch Processing"}


def _nav_titles(items):
    for item in items:
        if isinstance(item, dict):
            for title, value in item.items():
                yield title
                if isinstance(value, list):
                    yield from _nav_titles(value)


def test_sidebar_titles_are_short():
    import yaml

    config = yaml.safe_load(
        (REPO / "mkdocs.yml").read_text().replace("!!python/name:", "")
    )
    long = [
        t for t in _nav_titles(config["nav"]) if len(t) > 24 and t not in _LONG_TITLES
    ]
    assert not long, f"sidebar titles over 24 characters: {long}"


def test_no_heading_starts_with_a_number():
    numbered = []
    for page in (REPO / "docs").rglob("*.md"):
        in_code = False
        for line in page.read_text().splitlines():
            if line.startswith("```"):
                in_code = not in_code
            elif not in_code and re.match(r"#+ +\d", line):
                numbered.append(f"{page.relative_to(REPO)}: {line}")
    assert not numbered, numbered


def test_skill_is_generated_from_the_registry(gen_pages):
    committed = (REPO / "skills" / "odctl" / "SKILL.md").read_text()
    assert committed == gen_pages.skill(INTERNAL_RESOURCES_DIR), (
        "skills/odctl/SKILL.md is out of date; run uv run python scripts/gen_pages.py"
    )
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    for stack in registry.stacks.values():
        for profile in stack.profiles:
            assert f"\n### {profile}\n" in committed, (
                f"{profile} missing from the skill"
            )


def test_guide_code_blocks_are_copies_of_snippet_files():
    """Each block on a taught page is a copy of a snippet file, or a section of
    one, that the e2e test runs. Blocks that only start profiles with odctl are
    exempt, because the e2e test starts each profile itself, and so is output
    shown as text."""
    for page in TAUGHT_PAGES:
        for lang, info, body in FENCE.findall(page.read_text()):
            if lang == "text":
                continue
            code = [line for line in body.splitlines() if line.strip()]
            title = TITLE.search(info)
            if title is None:
                assert lang == "bash" and all(c.startswith("odctl ") for c in code), (
                    f"{page.name}: a {lang} block has no title naming its snippet file"
                )
                continue
            ref = title.group(1)
            path_text, _, name = ref.partition(":")
            path = REPO / path_text
            assert path_text.startswith("docs/snippets/") and path.exists(), (
                f"{page.name}: {ref} is not a snippet file"
            )
            expected = section(path, name) if name else path.read_text()
            assert body.rstrip("\n") == expected.rstrip("\n"), (
                f"{page.name}: the block titled {ref} differs from its file"
            )


def test_snippet_changes_select_the_groups_that_run_them():
    selector = load(
        "select_profiles", REPO / ".github" / "scripts" / "select-profiles.py"
    )
    registry = INTERNAL_RESOURCES_DIR / "registry.yml"
    folders = {p.name for p in (REPO / "docs" / "snippets").iterdir() if p.is_dir()}
    assert folders == set(selector.SNIPPET_GROUPS), (
        "add each docs/snippets folder to SNIPPET_GROUPS in select-profiles.py"
    )
    for groups in selector.SNIPPET_GROUPS.values():
        assert set(groups) <= set(selector.GROUPS)
    assert selector.select(["docs/snippets/kafka/commands.sh"], registry) == [
        "kafka-lite kafka-full"
    ]
    assert "spark-lite spark-full" in selector.select(
        ["src/odctl/resources/compose-kafka.yml"], registry
    )
    assert {"flink-lite flink-full", "airflow"} <= set(
        selector.select(["src/odctl/resources/compose-mlops.yml"], registry)
    )
    assert "flink-lite flink-full" in selector.select(
        ["src/odctl/resources/compose-kafka.yml"], registry
    )
    assert "fluss" in selector.select(
        ["src/odctl/resources/compose-flink.yml"], registry
    )
    assert "kafka-lite kafka-full" in selector.select(
        ["src/odctl/resources/compose-infra.yml"], registry
    )
    assert selector.select(["docs/snippets/unknown/x.sh"], registry) == list(
        selector.GROUPS
    )
    assert selector.select(["docs/snippets/rolling-windows/steps.sql"], registry) == [
        "flink-lite flink-full"
    ]
    assert set(
        selector.select(["docs/snippets/feast-iceberg/steps.sql"], registry)
    ) == {"feast", "flink-lite flink-full", "mlflow", "airflow"}


def test_pages_keep_within_the_heading_limits():
    """A page has at most 10 `##` headings and 15 headings below its title, as
    the docs guide sets; a longer page is split into a topic folder."""
    over = []
    for page in (REPO / "docs").rglob("*.md"):
        if "snippets" in page.parts:
            continue
        headings = []
        in_code = False
        for line in page.read_text().splitlines():
            if line.startswith("```"):
                in_code = not in_code
            elif not in_code and re.match(r"#{2,6} ", line):
                headings.append(line)
        second = [h for h in headings if h.startswith("## ")]
        if len(second) > 10 or len(headings) > 15:
            over.append(
                f"{page.relative_to(REPO)}: {len(second)} ##, {len(headings)} in all"
            )
    assert not over, over


def test_metadata_example_groups_are_selected_wherever_metadata_is():
    selector = load(
        "select_profiles", REPO / ".github" / "scripts" / "select-profiles.py"
    )
    registry = INTERNAL_RESOURCES_DIR / "registry.yml"
    groups = ["metadata", "metadata:deps", "metadata:autopilot"]
    # The two snippet folders the metadata cases read select exactly the metadata
    # groups whose smoke.sh case runs them; how-it-works also selects mlflow.
    for changed, runs_it in (
        ("docs/snippets/openmetadata/commands.sh", {"metadata", "metadata:autopilot"}),
        (
            "docs/snippets/how-it-works/commands.sh",
            {"metadata:deps", "metadata:autopilot", "mlflow"},
        ),
    ):
        selected = set(selector.select([changed], registry))
        assert runs_it <= selected, changed
        assert not (set(groups) - runs_it) & selected, changed
    assert (
        selector.select(["src/odctl/resources/compose-metadata.yml"], registry)
        == groups
    )
    for group in ("metadata:deps", "metadata:autopilot"):
        assert group not in selector.select(
            ["src/odctl/resources/compose-orch.yml"], registry
        )
    # Without a case, smoke.sh falls through to its default and passes silently.
    smoke = (REPO / ".github" / "scripts" / "smoke.sh").read_text()
    for group in groups:
        assert re.search(rf"^  {group}\)", smoke, re.M), group
