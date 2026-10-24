"""Points the site's links to the repository at the release tag instead of `main`.

The Markdown links to files on `main`, so the pages read correctly on GitHub. A reader
of a release's docs needs the code of that release, which `main` can have moved past,
so each rendered page has its `blob/main/`, `tree/main/` and raw `main/` links
rewritten to the tag `v<version>`, with the version read from `pyproject.toml`. The
tag is pushed after the docs of the release are deployed, so these links answer once
it exists.

The rewrite runs on `on_page_content`, before the llmstxt plugin turns the same HTML
into `llms-full.txt`, so the files for AI assistants carry the tag as well. A hook
runs after the plugins of the same priority, hence the higher priority.

The version is read with a regular expression rather than `tomllib`, which Python
3.10, the oldest version odctl supports, does not have.
"""

import re
from pathlib import Path

from mkdocs.plugins import event_priority

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
_REPOSITORY = "jaehyeon-kim/odctl"
_PREFIXES = (
    f"https://github.com/{_REPOSITORY}/blob/",
    f"https://github.com/{_REPOSITORY}/tree/",
    f"https://raw.githubusercontent.com/{_REPOSITORY}/",
)

_tag = ""


def release_tag() -> str:
    """
    Read the tag of the version in `pyproject.toml`.

    Returns:
        str: The tag, such as `v1.2.0`.

    Raises:
        ValueError: When the `[project]` table has no version.
    """
    text = _PYPROJECT.read_text(encoding="utf-8")
    project = text.split("[project]", 1)[1].split("\n[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if match is None:
        raise ValueError(f"no version in the [project] table of {_PYPROJECT}")
    return "v" + match.group(1)


def _to_release(html: str, tag: str) -> str:
    """Point every link to a file on `main` in `html` at `tag`.

    Args:
        html (str): A rendered page.
        tag (str): The release tag, such as `v1.2.0`.

    Returns:
        str: The page with `blob/main/`, `tree/main/` and raw `main/` links on the tag.
    """
    for prefix in _PREFIXES:
        html = html.replace(prefix + "main/", f"{prefix}{tag}/")
    return html


def on_config(config):
    """Read the release tag for this build; MkDocs calls it once per build.

    Read on every build, so `mkdocs serve` follows a version bump.

    Args:
        config: The MkDocs config.

    Returns:
        The config, unchanged.
    """
    global _tag
    _tag = release_tag()
    return config


@event_priority(50)
def on_page_content(html, page, config, files):
    """Point the links of each rendered page at the release tag; MkDocs calls it per page.

    Args:
        html: The page's HTML.
        page: The page.
        config: The MkDocs config.
        files: The site's files.

    Returns:
        str: The HTML with links to files on `main` pointed at the release tag.
    """
    return _to_release(html, _tag)
