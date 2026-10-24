"""Every diagram source has its exported image, and every GIF has its still.

The sources are draw.io files under docs/assets/diagrams/, exported by
scripts/diagrams.py to a PNG or a GIF beside them. Files whose name starts with an
underscore hold the shared shapes and are not exported.

Every GIF has a still beside it: a PNG of the same name, its last frame, for a reader
or a format that does not play a GIF. No page needs to use a still, so the check that
every image is used on a page leaves the stills out.
"""

from docs_helpers import REPO

DIAGRAMS = REPO / "docs" / "assets" / "diagrams"
IMAGE_SUFFIXES = (".png", ".gif")
# A GIF stays under a few hundred KB, so a page with one loads quickly
MAX_GIF_BYTES = 300_000
# The README's recording and diagram stay in image/: the PyPI page of every released
# version links them there on main, so moving them would break those pages.
GIF_FOLDERS = (REPO / "docs", REPO / "image")


def _is_still(path):
    """Tell whether a file is the still PNG of a GIF beside it.

    Args:
        path (Path): The image file.

    Returns:
        bool: True when `path` is a PNG and a GIF of the same name sits beside it.
    """
    return path.suffix == ".png" and path.with_suffix(".gif").exists()


def test_every_diagram_has_its_image():
    missing = []
    for source in sorted(DIAGRAMS.glob("*.drawio")):
        if source.name.startswith("_"):
            continue
        if not any(source.with_suffix(s).exists() for s in IMAGE_SUFFIXES):
            missing.append(source.name)
    assert not missing, f"Run scripts/diagrams.py to export: {missing}"


def test_every_image_is_used_on_a_page():
    pages = "\n".join(p.read_text() for p in (REPO / "docs").rglob("*.md"))
    unused = []
    for image in sorted((REPO / "docs").rglob("*")):
        if image.suffix not in IMAGE_SUFFIXES or _is_still(image):
            continue
        if image.parent.name not in {"images", "diagrams"}:
            continue
        if f"{image.parent.name}/{image.name}" not in pages:
            unused.append(image.name)
    assert not unused, f"No page uses these images: {unused}"


def test_every_gif_has_its_still_and_is_small():
    gifs = []
    for folder in GIF_FOLDERS:
        gifs += sorted(folder.rglob("*.gif"))
    no_still = [str(p) for p in gifs if not p.with_suffix(".png").exists()]
    large = []
    for gif in gifs:
        if gif.stat().st_size > MAX_GIF_BYTES:
            large.append(f"{gif} ({gif.stat().st_size} bytes)")
    assert gifs
    assert not no_still, f"Run scripts/diagrams.py to write their stills: {no_still}"
    assert not large, f"Make these smaller than {MAX_GIF_BYTES} bytes: {large}"
