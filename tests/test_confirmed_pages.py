"""Pages the owner has confirmed keep their exact text.

Why odctl is the owner's own story, confirmed as written. A docs revision must not
reword it. Change it only when the owner asks, then record the new hash here.
"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFIRMED = {
    "docs/about/why-odctl.md": "9bfddf24c515e1467571ca5ee2dccabd4c83ca9fe08ff172ce55645fc3758047",
}


def test_confirmed_pages_are_unchanged():
    changed = [
        path
        for path, digest in CONFIRMED.items()
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest
    ]
    assert not changed, f"Owner-confirmed pages changed; ask the owner first: {changed}"
