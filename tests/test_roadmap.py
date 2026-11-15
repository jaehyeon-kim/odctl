"""The public roadmap follows the version in `pyproject.toml`.

Only Released names versions: an item in Now or Planned gets its version when it
ships. The release commit bumps the version and, in the same commit, moves the release
from Now to Released. These tests fail when a release is tagged with the roadmap still
showing it as current, or when a coming item names a version that can go stale.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_ROADMAP = (ROOT / "docs" / "about" / "roadmap.md").read_text()
# tomllib needs Python 3.11, and odctl supports 3.10.
_VERSION_LINE = re.search(
    r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.MULTILINE
)
assert _VERSION_LINE is not None
_VERSION = _VERSION_LINE.group(1)
_COMING, _RELEASED = _ROADMAP.split("\n## Released\n", 1)
# A YAML single-quoted title writes a quote as two, as in 'SimPy''s examples'
_ENTRIES = re.findall(
    r"^- title: '((?:[^']|'')*)'\n((?:  .*\n)+)", _COMING, re.MULTILINE
)


def test_the_current_version_is_under_released():
    assert f'??? note "{_VERSION}:' in _RELEASED


def test_nothing_still_to_come_names_a_version():
    headings = re.findall(
        r"^(?:- title: '|-   __)(.*?)(?:'|__)$", _COMING, re.MULTILINE
    )
    assert headings
    assert [h for h in headings if re.search(r"\d+\.\d+\.\d+", h)] == []


def test_at_most_one_entry_is_current():
    now = [title for title, body in _ENTRIES if "  key: now\n" in body]
    assert len(now) <= 1


def test_the_current_entry_names_its_issue():
    # The release's Changelog section links the same issue.
    missing = [
        title
        for title, body in _ENTRIES
        if "  key: now\n" in body and not re.search(r"/issues/\d+\)", body)
    ]
    assert missing == []
