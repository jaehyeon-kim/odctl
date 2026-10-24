"""The docs link to files on `main`, and the built site points them at the
release tag, through the hook `scripts/release_links.py`."""

import re

import yaml

from docs_helpers import REPO, load

_RELEASE_HOOK = REPO / "scripts" / "release_links.py"
_REPO_URL = "https://github.com/jaehyeon-kim/odctl"
_RAW_URL = "https://raw.githubusercontent.com/jaehyeon-kim/odctl"


def test_built_page_links_to_the_release_tag(tmp_path):
    """The Markdown links to files on `main`, and the hook rewrites them to
    `v<version>` in the rendered page."""
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    release_links = load("release_links", _RELEASE_HOOK)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(
        f"[A file]({_REPO_URL}/blob/main/skills/odctl/SKILL.md) and "
        f"[a folder]({_REPO_URL}/tree/main/docs/snippets).\n\n"
        f"```bash\ncurl -O {_RAW_URL}/main/README.md\n```\n"
    )
    (tmp_path / "mkdocs.yml").write_text(
        f"site_name: Links\nhooks:\n  - {_RELEASE_HOOK}\n"
    )
    build(load_config(str(tmp_path / "mkdocs.yml"), site_dir=str(tmp_path / "site")))

    html = (tmp_path / "site" / "index.html").read_text()
    tag = release_links.release_tag()
    assert re.fullmatch(r"v\d+\.\d+\.\d+", tag)
    assert "/main/" not in html
    assert f"{_REPO_URL}/blob/{tag}/skills/odctl/SKILL.md" in html
    assert f"{_REPO_URL}/tree/{tag}/docs/snippets" in html
    assert f"{_RAW_URL}/{tag}/README.md" in html


def test_site_loads_the_release_links_hook():
    config = yaml.safe_load(
        (REPO / "mkdocs.yml").read_text().replace("!!python/name:", "")
    )
    assert "scripts/release_links.py" in config["hooks"]
