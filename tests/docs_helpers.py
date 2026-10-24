"""Helpers the docs tests share: the repository root, loading a script as a
module, and the titled code blocks of the pages that teach odctl."""

import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    """Import the script at `path` as a module named `name`."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FENCE = re.compile(r"^```(\w+)([^\n]*)\n(.*?)^```", re.S | re.M)
TITLE = re.compile(r'title="([^"]+)"')


def section(path: Path, name: str) -> str:
    """The lines between `--8<-- [start:name]` and `[end:name]` in `path`."""
    lines: list[str] = []
    inside = False
    for line in path.read_text().splitlines():
        if f"--8<-- [start:{name}]" in line:
            inside = True
        elif f"--8<-- [end:{name}]" in line:
            return "\n".join(lines)
        elif inside:
            lines.append(line)
    raise AssertionError(f"no section {name} in {path.relative_to(REPO)}")


# Pages whose code blocks are copies of snippet files: the guides, and the two
# pages that teach the commands.
TAUGHT_PAGES = [
    *sorted((REPO / "docs" / "guides").glob("*.md")),
    REPO / "docs" / "getting-started.md",
    REPO / "docs" / "how-it-works.md",
]


def titled_blocks():
    """Each code block with a title on the taught pages, as (page, ref, body)."""
    for page in TAUGHT_PAGES:
        for _, info, body in FENCE.findall(page.read_text()):
            title = TITLE.search(info)
            if title:
                yield page, title.group(1), body
