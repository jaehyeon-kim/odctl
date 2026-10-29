"""The connector sync of the metadata profile, run against a stubbed S3 client.

The module is a resource file that the ingestion container mounts, not part of the
odctl package, so it is loaded from its path. Nothing here needs Docker or boto3.
"""

import importlib.util

import pytest

from odctl.config import get_internal_resources_dir

_PATH = get_internal_resources_dir() / "openmetadata" / "connector_sync.py"
_SPEC = importlib.util.spec_from_file_location("connector_sync", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sync = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sync)


class FakeS3:
    """Holds objects as {key: (etag, body)} and fails on demand."""

    def __init__(self, objects=None):
        self.objects = objects or {}
        self.failures = 0
        self.download_failures = 0
        self.downloads = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("S3 is not reachable")
        keys = [k for k in sorted(self.objects) if k.startswith(Prefix)]
        # Two pages, to show that a listing reads every page.
        half = len(keys) // 2
        for chunk in (keys[:half], keys[half:]):
            yield {"Contents": [{"Key": k, "ETag": self.objects[k][0]} for k in chunk]}

    def download_file(self, bucket, key, path):
        if self.download_failures:
            self.download_failures -= 1
            raise ConnectionError("download failed")
        self.downloads.append(key)
        with open(path, "w") as file:
            file.write(self.objects[key][1])


def _files(folder):
    return {
        str(p.relative_to(folder)): p.read_text()
        for p in folder.rglob("*")
        if p.is_file()
    }


def test_an_empty_prefix_leaves_an_empty_folder(tmp_path):
    s3 = FakeS3()
    assert sync.first_copy(s3, str(tmp_path)) == []
    assert _files(tmp_path) == {}


def test_a_listing_skips_folder_markers_and_reads_every_page():
    s3 = FakeS3(
        {
            "connectors/": ("e0", ""),
            "connectors/a.py": ("e1", "A"),
            "connectors/pkg/b.py": ("e2", "B"),
            "connectors/pkg/c.py": ("e3", "C"),
            "other/x.py": ("e4", "X"),
        }
    )
    assert sync.listing(s3) == [
        ("connectors/a.py", "e1"),
        ("connectors/pkg/b.py", "e2"),
        ("connectors/pkg/c.py", "e3"),
    ]


def test_new_changed_and_deleted_files_are_copied(tmp_path):
    s3 = FakeS3({"connectors/a.py": ("e1", "A1")})
    objects = sync.first_copy(s3, str(tmp_path))
    assert _files(tmp_path) == {"a.py": "A1"}

    s3.objects["connectors/pkg/b.py"] = ("e2", "B1")
    objects = sync.sync_changes(s3, objects, str(tmp_path))
    assert _files(tmp_path) == {"a.py": "A1", "pkg/b.py": "B1"}

    s3.objects["connectors/a.py"] = ("e3", "A2")
    objects = sync.sync_changes(s3, objects, str(tmp_path))
    assert _files(tmp_path)["a.py"] == "A2"

    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.pyc").write_text("compiled")
    del s3.objects["connectors/pkg/b.py"]
    objects = sync.sync_changes(s3, objects, str(tmp_path))
    assert _files(tmp_path) == {"a.py": "A2", "__pycache__/a.pyc": "compiled"}


def test_folders_no_listed_file_is_in_are_removed_but_used_ones_keep_their_cache(
    tmp_path,
):
    s3 = FakeS3(
        {
            "connectors/a.py": ("e1", "A"),
            "connectors/pkg/sub/b.py": ("e2", "B"),
            "connectors/pkg/c.py": ("e3", "C"),
        }
    )
    objects = sync.first_copy(s3, str(tmp_path))
    (tmp_path / "pkg" / "sub" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "sub" / "__pycache__" / "b.pyc").write_text("compiled")
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "c.pyc").write_text("compiled")

    del s3.objects["connectors/pkg/sub/b.py"]
    sync.sync_changes(s3, objects, str(tmp_path))

    assert not (tmp_path / "pkg" / "sub").exists()
    assert (tmp_path / "pkg" / "__pycache__" / "c.pyc").exists()
    assert _files(tmp_path)["pkg/c.py"] == "C"


def test_an_unchanged_listing_copies_nothing(tmp_path):
    s3 = FakeS3({"connectors/a.py": ("e1", "A")})
    objects = sync.first_copy(s3, str(tmp_path))
    s3.downloads.clear()
    assert sync.sync_changes(s3, objects, str(tmp_path)) == objects
    assert s3.downloads == []


def test_a_failed_listing_keeps_the_files_and_the_old_listing(tmp_path, capsys):
    s3 = FakeS3({"connectors/a.py": ("e1", "A")})
    objects = sync.first_copy(s3, str(tmp_path))
    s3.failures = 1
    assert sync.sync_changes(s3, objects, str(tmp_path)) == objects
    assert _files(tmp_path) == {"a.py": "A"}
    assert "Syncing s3://openmetadata/connectors failed" in capsys.readouterr().out
    # The next pass works again.
    s3.objects["connectors/b.py"] = ("e2", "B")
    sync.sync_changes(s3, objects, str(tmp_path))
    assert "b.py" in _files(tmp_path)


def test_the_first_copy_retries_every_5_seconds_for_60_seconds(tmp_path):
    s3 = FakeS3({"connectors/a.py": ("e1", "A")})
    s3.failures = 3
    clock = {"now": 0.0}
    waits = []

    def sleep(seconds):
        waits.append(seconds)
        clock["now"] += seconds

    objects = sync.first_copy(s3, str(tmp_path), sleep, lambda: clock["now"])
    assert objects == [("connectors/a.py", "e1")]
    assert waits == [5, 5, 5]
    assert _files(tmp_path) == {"a.py": "A"}


def test_a_first_copy_that_never_works_gives_up_without_raising(tmp_path):
    s3 = FakeS3()
    s3.failures = 1000
    clock = {"now": 0.0}

    def sleep(seconds):
        clock["now"] += seconds

    assert sync.first_copy(s3, str(tmp_path), sleep, lambda: clock["now"]) is None
    assert clock["now"] == pytest.approx(60)


def test_a_listing_that_changes_after_a_failed_copy_is_tried_again(tmp_path):
    s3 = FakeS3({"connectors/a.py": ("e1", "A")})
    objects = sync.first_copy(s3, str(tmp_path))
    s3.objects["connectors/a.py"] = ("e2", "A2")
    s3.download_failures = 1
    assert sync.sync_changes(s3, objects, str(tmp_path)) == objects
    assert sync.sync_changes(s3, objects, str(tmp_path)) == [("connectors/a.py", "e2")]
    assert _files(tmp_path) == {"a.py": "A2"}
