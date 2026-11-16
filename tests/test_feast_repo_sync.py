"""The Feast services' start-up script, run with a fake S3 client.

Nothing here needs Docker or SeaweedFS.
"""

import sys
import types

import pytest
import yaml

from odctl.config import get_internal_resources_dir

RESOURCES = get_internal_resources_dir()


def _script():
    return yaml.safe_load((RESOURCES / "compose-mlops.yml").read_text())[
        "x-feast-repo-sync"
    ]


class _Gone(Exception):
    pass


def test_an_object_deleted_during_a_load_does_not_stop_the_service(
    monkeypatch, tmp_path
):
    # serve_repo.py clears s3://feast/repo and uploads again, so an object can
    # vanish between the listing and its download.
    downloads = []

    class Client:
        def get_paginator(self, _name):
            return self

        def paginate(self, **_kwargs):
            return [{"Contents": [{"Key": "repo/feature_store.yaml", "ETag": "1"}]}]

        def download_file(self, _bucket, key, path):
            downloads.append(key)
            if len(downloads) == 1:
                raise _Gone("HeadObject 404")
            open(path, "w").close()

    class Feast:
        returncode = 0

        def poll(self):
            return 0

    monkeypatch.setitem(
        sys.modules, "boto3", types.SimpleNamespace(client=lambda *a, **k: Client())
    )
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: Feast())
    monkeypatch.setattr("time.sleep", lambda _s: None)
    script = _script().replace('"/tmp/feature_repo"', repr(str(tmp_path / "repo")))
    with pytest.raises(SystemExit) as stopped:
        exec(compile(script, "feast-repo-sync", "exec"), {"__name__": "__main__"})
    assert stopped.value.code == 0
    assert downloads == ["repo/feature_store.yaml", "repo/feature_store.yaml"]


def test_a_failed_listing_during_a_load_does_not_stop_the_service(
    monkeypatch, tmp_path
):
    # SeaweedFS can be unreachable for a moment, such as while it restarts.
    listings = []

    class Client:
        def get_paginator(self, _name):
            return self

        def paginate(self, **_kwargs):
            listings.append(1)
            if len(listings) == 1:
                raise _Gone("Could not connect to the endpoint URL")
            return [{"Contents": [{"Key": "repo/feature_store.yaml", "ETag": "1"}]}]

        def download_file(self, _bucket, _key, path):
            open(path, "w").close()

    class Feast:
        returncode = 0

        def poll(self):
            return 0

    monkeypatch.setitem(
        sys.modules, "boto3", types.SimpleNamespace(client=lambda *a, **k: Client())
    )
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: Feast())
    monkeypatch.setattr("time.sleep", lambda _s: None)
    script = _script().replace('"/tmp/feature_repo"', repr(str(tmp_path / "repo")))
    with pytest.raises(SystemExit) as stopped:
        exec(compile(script, "feast-repo-sync", "exec"), {"__name__": "__main__"})
    assert stopped.value.code == 0
    assert len(listings) == 2
    assert (tmp_path / "repo" / "feature_store.yaml").exists()
