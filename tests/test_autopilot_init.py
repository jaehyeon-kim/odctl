"""The AutoPilot setting of the metadata profile, run against a stubbed API.

The module is a resource file that the `openmetadata-init` container mounts, not
part of the odctl package, so it is loaded from its path. Nothing here needs Docker.
"""

import importlib.util
import urllib.error

import pytest

from odctl.config import get_internal_resources_dir

_PATH = get_internal_resources_dir() / "openmetadata" / "autopilot_init.py"
_SPEC = importlib.util.spec_from_file_location("autopilot_init", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
init = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(init)


class FakeApi:
    """Records the calls, fails the first `failures` of them, and refuses a login for
    each address in `refused` with HTTP `status`."""

    def __init__(self, failures=0, refused=(), status=400):
        self.calls = []
        self.refused = refused
        self.status = status
        self.failures = failures
        self.active = True

    def __call__(self, method, path, body=None, token=None, content_type=None):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("server not ready")
        self.calls.append((method, path, body))
        if path == "/users/login":
            if body["email"] in self.refused:
                raise urllib.error.HTTPError(path, self.status, "Refused", None, None)
            return {"accessToken": "jwt"}
        if method == "PATCH":
            assert token == "jwt"
            assert content_type == "application/json-patch+json"
            self.active = body[0]["value"]
        return {"appConfiguration": {"active": self.active}}


def test_only_the_word_true_turns_autopilot_on():
    assert init.wanted("true") and init.wanted(" True ")
    assert not init.wanted("false") and not init.wanted("") and not init.wanted("1")


def test_the_value_is_set_applied_and_read_back():
    api = FakeApi()
    assert init.apply(False, api, lambda _: None) is False
    assert [(m, p) for m, p, _ in api.calls] == [
        ("POST", "/users/login"),
        ("PATCH", "/apps/name/AutoPilotApplication"),
        ("POST", "/apps/configure/AutoPilotApplication"),
        ("GET", "/apps/name/AutoPilotApplication?fields=appConfiguration"),
    ]
    assert api.calls[1][2] == [
        {"op": "add", "path": "/appConfiguration/active", "value": False}
    ]


def test_a_server_that_is_not_ready_is_tried_again():
    api = FakeApi(failures=3)
    waits = []
    assert init.apply(True, api, waits.append) is True
    assert waits == [5, 5, 5]


def test_a_server_that_never_answers_gives_none_after_12_tries():
    api = FakeApi(failures=1000)
    waits = []
    assert init.apply(True, api, waits.append) is None
    assert len(waits) == 11


def test_main_prints_the_state_and_exits_normally_even_when_it_cannot_set_it(
    monkeypatch, capsys
):
    monkeypatch.setenv("METADATA_AUTOPILOT", "false")
    monkeypatch.setattr(init, "apply", lambda active: False)
    init.main()
    assert capsys.readouterr().out.strip() == "AutoPilot active: false"

    monkeypatch.setattr(init, "apply", lambda active: None)
    init.main()
    assert "could not be set" in capsys.readouterr().out


@pytest.mark.parametrize("status", [400, 401])
def test_a_database_from_an_earlier_release_logs_in_with_the_old_domain(status):
    api = FakeApi(refused=("admin@odctl.io",), status=status)
    assert init.apply(False, api, lambda _: None) is False
    emails = [b["email"] for m, p, b in api.calls if p == "/users/login"]
    assert emails == ["admin@odctl.io", "admin@open-data.local"]
    assert ("PATCH", "/apps/name/AutoPilotApplication") in [
        (m, p) for m, p, _ in api.calls
    ]


def test_both_addresses_refused_gives_none_without_retrying():
    api = FakeApi(refused=("admin@odctl.io", "admin@open-data.local"))
    waits = []
    assert init.apply(False, api, waits.append) is None
    assert waits == []
    assert [p for _, p, _ in api.calls] == ["/users/login", "/users/login"]


def test_a_login_error_that_is_not_a_refusal_is_tried_again():
    api = FakeApi(refused=("admin@odctl.io",), status=500)
    waits = []
    assert init.apply(False, api, waits.append) is None
    assert len(waits) == 11
