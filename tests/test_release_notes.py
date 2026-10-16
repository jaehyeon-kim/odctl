"""A GitHub release's text is its version's section of the docs Changelog."""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_notes.py"
_spec = importlib.util.spec_from_file_location("release_notes", _SCRIPT)
assert _spec is not None and _spec.loader is not None
release_notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_notes)

CHANGELOG = """# Changelog

Intro.

## Version 1.1.0

Ports bind to 127.0.0.1. See [How it works](../how-it-works.md#how-you-reach-a-service) and the [home page](../index.md).

### Upgrading

- One line.

## Version 1.0.2

Python 3.15.
"""


def test_section_is_the_body_without_its_heading():
    body = release_notes.section("1.1.0", CHANGELOG)
    assert body.startswith("Ports bind to 127.0.0.1.")
    assert "### Upgrading\n\n- One line." in body
    assert "1.0.2" not in body and "## Version" not in body


def test_the_last_section_runs_to_the_end():
    assert release_notes.section("1.0.2", CHANGELOG) == "Python 3.15.\n"


def test_relative_links_point_at_the_latest_docs():
    body = release_notes.section("1.1.0", CHANGELOG)
    assert (
        "](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service)"
        in body
    )
    assert "](https://jaehyeon.me/odctl/latest/)" in body


def test_a_missing_version_is_an_error():
    with pytest.raises(ValueError):
        release_notes.section("9.9.9", CHANGELOG)


def test_the_published_changelog_has_the_current_version():
    version = next(
        line.split('"')[1]
        for line in (_SCRIPT.parents[1] / "pyproject.toml").read_text().splitlines()
        if line.startswith("version = ")
    )
    assert release_notes.section(version, release_notes.CHANGELOG.read_text())


def test_notes_end_with_the_full_changelog_link():
    tags = ["v1.0.1", "v1.0.2", "v1.1.0", "v0.10.0", "not-a-release"]
    body = release_notes.notes("1.1.0", CHANGELOG, tags)
    assert body.endswith(
        "\n**Full Changelog**: https://github.com/jaehyeon-kim/odctl/compare/v1.0.2...v1.1.0\n"
    )


def test_the_previous_tag_compares_versions_as_numbers():
    assert release_notes.previous_tag("1.0.0", ["v0.9.0", "v0.10.0"]) == "v0.10.0"
    assert release_notes.previous_tag("0.1.0", ["v0.1.0"]) is None
