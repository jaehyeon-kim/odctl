"""Every feature a user can reach has its docs: a tested example, a reference
entry, a place in the skill and, for a command, a README line."""

import re

import pytest

from docs_helpers import REPO, load, titled_blocks
from odctl.config import INTERNAL_RESOURCES_DIR


@pytest.fixture(scope="module")
def gen_pages():
    return load("gen_pages", REPO / "scripts" / "gen_pages.py")


@pytest.fixture(scope="module")
def pages(gen_pages):
    return gen_pages.profile_pages(INTERNAL_RESOURCES_DIR)


# Features that have no tested example on a taught page, each with the reason.
_UNTAUGHT = {
    "option --verbose": "prints debug logs, whose lines change with every release",
    "option pull --all": "downloads the images of every profile, many GB; How It Works names it",
    "option logs --follow": "runs until Ctrl+C; Getting Started names it",
    "profile deps": "every other profile starts it; How It Works explains it",
    "profile kafka-full": "runs the Kafka guide's commands with the container kafka-1; the e2e kafka-full case runs them",
    "profile flink-full": "runs the same SQL as flink-lite; the e2e flink-full case runs it",
    "profile spark-full": "runs the same jobs as spark-lite; the e2e spark-full case runs them",
}


def _features(gen_pages):
    """Every feature a user can reach: commands, their options, profiles and
    the `.env` keys `odctl init` writes, each with the text that shows it used."""
    for name in gen_pages.visible_commands():
        yield f"command {name}", [rf"\bodctl {name}\b"]
    for command, flags, _ in gen_pages.command_options():
        forms = [re.escape(f) for f in flags.split(", ")]
        where = r"\bodctl\b.*" if not command else rf"\bodctl {command}\b.*"
        yield (
            f"option {command + ' ' if command else ''}{flags.split(', ')[0]}",
            [where + rf"(?<![\w-]){f}(?![\w-])" for f in forms],
        )
    registry = gen_pages.load_registry(INTERNAL_RESOURCES_DIR)
    for stack in registry.stacks.values():
        for profile in stack.profiles:
            yield (
                f"profile {profile}",
                [rf"\bodctl (up|pull|recreate)\b.*(?<![\w-]){profile}(?![\w-])"],
            )
    for key in gen_pages.env_keys():
        yield f"setting {key}", [rf"(?<![\w-]){key}="]


def _is_tested(patterns, example_lines) -> bool:
    """Whether any line of a titled code block uses the feature."""
    for pattern in patterns:
        if any(re.search(pattern, line) for line in example_lines):
            return True
    return False


def _reference_gaps(kind, name, docs) -> list:
    """What a feature of this kind lacks in the reference, skill and README."""
    if kind == "command":
        readme_link = (
            f"[`odctl {name}`](https://jaehyeon.me/odctl/latest/cli/#odctl-{name})"
        )
        checks = [
            (f"\n## odctl {name}\n" in docs["reference"], "no CLI reference section"),
            (f"`odctl {name}`" in docs["skill"], "not in the skill"),
            (readme_link in docs["readme"], "no README Commands line"),
        ]
    elif kind == "option":
        flag = name.split()[-1]
        checks = [
            (flag in docs["reference"], "not in the CLI reference"),
            (f"`{flag}" in docs["skill"], "not in the skill"),
        ]
    elif kind == "profile":
        checks = [
            (f"\n### {name}\n" in docs["profiles"], "no profile page section"),
            (f"\n### {name}\n" in docs["skill"], "not in the skill"),
        ]
    else:
        checks = [
            (f"`{name}`" in docs["workspace"], "not in How It Works"),
            (f"`{name}`" in docs["skill"], "not in the skill"),
        ]
    gaps = []
    for present, gap in checks:
        if not present:
            gaps.append(gap)
    return gaps


def test_every_feature_has_its_docs(gen_pages, pages):
    """A feature merges only with its docs: a tested example on a guide, Getting
    Started or How It Works, a reference entry, a place in the skill, and for a
    command a line in the README's Commands section."""
    example_lines = "\n".join(body for _, _, body in titled_blocks()).splitlines()
    docs = {
        "reference": gen_pages.cli_reference(),
        "profiles": "".join(pages.values()),
        "workspace": (REPO / "docs" / "how-it-works.md").read_text(),
        "skill": (REPO / "skills" / "odctl" / "SKILL.md").read_text(),
        "readme": (REPO / "README.md").read_text(),
    }
    features = dict(_features(gen_pages))
    missing = []
    for feature, patterns in features.items():
        kind, _, name = feature.partition(" ")
        if not _is_tested(patterns, example_lines) and feature not in _UNTAUGHT:
            missing.append(f"{feature}: no tested example")
        missing.extend(f"{feature}: {gap}" for gap in _reference_gaps(kind, name, docs))
    stale = sorted(set(_UNTAUGHT) - set(features))
    assert not stale, f"exceptions for features that no longer exist: {stale}"
    assert not missing, "\n".join(missing)
