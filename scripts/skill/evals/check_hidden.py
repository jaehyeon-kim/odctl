"""Checks that no file of a reviewer's folder names the version of the run it holds.

Usage:

    python check_hidden.py FOLDER...

Each FOLDER is searched through, every file in it read as text (a `.gz` file unpacked). A
file fails when it names a suite or a version: `suite-a` or `suite-b` as a word, an odctl
version such as `1.9.0` after `odctl` or `TAG=`, or `before` or `after` as a part of a path
(`before/`, `/after`). The script prints each file and line that does, and exits 1 when there
is one. It exits 2 when a FOLDER is not a folder or holds no file, or when a file or a
folder in it cannot be read, because each would otherwise search nothing and pass. `facts.py`
writes the folders this checks (`--out`), and `run_task.md` step 6 runs it on all of them.
"""

import gzip
import os
import re
import sys
import zlib
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

NAMES = re.compile(
    r"(?<![\w-])(?:suite-a|suite-b)(?![\w-])"
    r"|(?:odctl[ =/@:-]+v?|\bTAG=)\d+\.\d+\.\d+(?![\w.])"
    r"|(?<![\w-])(?:before|after)(?=/)"
    r"|(?<=/)(?:before|after)(?![\w-])"
)


def files_in(folder: Path) -> List[Path]:
    """Returns every file under a folder; a folder in it that cannot be read raises OSError."""

    def fail(error: OSError) -> None:
        # Why: os.walk skips a folder it cannot list unless told to raise
        raise error

    found = []
    for top, _, names in os.walk(folder, onerror=fail):
        found += [Path(top) / name for name in names if (Path(top) / name).is_file()]
    return sorted(found)


def _texts(folder: Path) -> Iterator[Tuple[Path, str]]:
    """Yields each file under a folder with its text."""
    for path in files_in(folder):
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                yield path, f.read()
        else:
            yield path, path.read_text("utf-8", "replace")


def leaks(folder: Path) -> List[str]:
    """Returns `FILE:LINE: NAME` for each name of a version in a folder's files."""
    found = []
    for path, text in _texts(folder):
        for number, line in enumerate(text.splitlines(), 1):
            for match in NAMES.finditer(line):
                found.append(f"{path}:{number}: {match.group(0)}")
    return found


def main(argv: Optional[List[str]] = None) -> int:
    """Checks each folder given; returns 1 when a file names a version, 2 when a folder is
    not one, holds no file or cannot be read."""
    folders = [Path(a) for a in (sys.argv[1:] if argv is None else argv)]
    if not folders:
        print(__doc__)
        return 2
    absent = [folder for folder in folders if not folder.is_dir()]
    for folder in absent:
        print(f"check_hidden.py: {folder} is not a folder", file=sys.stderr)
    if absent:
        return 2
    found = []
    unread = False
    for folder in folders:
        try:
            if not files_in(folder):
                # Why: a folder an interrupted copy left empty has nothing to search
                print(f"check_hidden.py: {folder} holds no file", file=sys.stderr)
                unread = True
                continue
            found += leaks(folder)
        except (OSError, EOFError, zlib.error) as error:
            # Why: a file not read is a file not searched; EOFError is a cut gzip file
            print(f"check_hidden.py: cannot read {folder}: {error}", file=sys.stderr)
            unread = True
    for text in found:
        print(text)
    if unread:
        return 2
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
