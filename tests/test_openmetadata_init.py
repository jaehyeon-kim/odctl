"""The AutoPilot setting and the users' roles of the metadata profile, run against a
stubbed API.

The module is a resource file that the `openmetadata-init` container mounts, not
part of the odctl package, so it is loaded from its path. Nothing here needs Docker.
"""

import base64
import importlib.util
import urllib.error

import pytest

from odctl.config import get_internal_resources_dir

_PATH = get_internal_resources_dir() / "openmetadata" / "openmetadata_init.py"
_SPEC = importlib.util.spec_from_file_location("openmetadata_init", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
init = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(init)


class FakeApi:
    """Records the calls, fails the first `failures` of them, and refuses each login
    in `refused`, an email and its plain password, with HTTP `status`."""

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
            login = (body["email"], base64.b64decode(body["password"]).decode())
            if login in self.refused:
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
    monkeypatch.setattr(
        init, "set_roles", lambda: {"steward": ["DataSteward"], "viewer": ["Viewer"]}
    )
    init.main()
    assert capsys.readouterr().out.splitlines() == [
        "AutoPilot active: false",
        "steward roles: DataSteward",
        "viewer roles: Viewer",
    ]

    monkeypatch.setattr(init, "apply", lambda active: None)
    monkeypatch.setattr(init, "set_roles", lambda: None)
    init.main()
    out = capsys.readouterr().out
    assert "AutoPilot could not be set" in out
    assert "The users' roles could not be set" in out


@pytest.mark.parametrize("status", [400, 401])
def test_a_database_from_an_earlier_release_logs_in_with_its_own_admin(status):
    refused = tuple(init.LOGINS[:2])
    api = FakeApi(refused=refused, status=status)
    assert init.apply(False, api, lambda _: None) is False
    emails = [b["email"] for m, p, b in api.calls if p == "/users/login"]
    assert emails == ["admin@odctl.io", "admin@odctl.io", "admin@open-data.local"]
    assert ("PATCH", "/apps/name/AutoPilotApplication") in [
        (m, p) for m, p, _ in api.calls
    ]


def test_every_login_refused_gives_none_without_retrying():
    api = FakeApi(refused=tuple(init.LOGINS))
    waits = []
    assert init.apply(False, api, waits.append) is None
    assert waits == []
    assert [p for _, p, _ in api.calls] == ["/users/login"] * len(init.LOGINS)


def test_a_login_error_that_is_not_a_refusal_is_tried_again():
    api = FakeApi(refused=(init.LOGINS[0],), status=500)
    waits = []
    assert init.apply(False, api, waits.append) is None
    assert len(waits) == 11


class FakeServer:
    """Keeps policies, roles and users' roles as the server would. In each of the first
    `failing_runs` runs, a run being one login and the calls after it, the call
    numbered `fail_at` (from 0) fails with HTTP 500."""

    def __init__(self, fail_at=None, failing_runs=1000):
        self.calls = []
        self.fail_at = fail_at
        self.failing_runs = failing_runs
        self.runs = 0
        self.run_calls = 0
        self.policies = {}
        self.roles = {"DataSteward": "id-ds"}
        self.user_ids = {"steward": "id-steward", "viewer": "id-viewer"}
        self.user_roles = {"id-steward": [], "id-viewer": []}

    def __call__(self, method, path, body=None, token=None, content_type=None):
        self.calls.append((method, path, body))
        if path == "/users/login":
            self.runs += 1
            self.run_calls = 0
            return {"accessToken": "jwt"}
        if self.run_calls == self.fail_at and self.runs <= self.failing_runs:
            self.run_calls += 1
            raise urllib.error.HTTPError(path, 500, "Error", None, None)
        self.run_calls += 1
        assert token == "jwt"
        if (method, path) == ("PUT", "/policies"):
            self.policies[body["name"]] = body
            return body
        if (method, path) == ("PUT", "/roles"):
            assert all(name in self.policies for name in body["policies"])
            self.roles.setdefault(body["name"], f"id-{body['name']}")
            return body
        if method == "GET" and path.startswith("/roles/name/"):
            return {"id": self.roles[path.rsplit("/", 1)[1]]}
        if method == "GET" and path.endswith("?fields=roles"):
            user_id = self.user_ids[path.split("/")[3].split("?")[0]]
            names = {v: k for k, v in self.roles.items()}
            return {
                "roles": [{"name": names[r["id"]]} for r in self.user_roles[user_id]]
            }
        if method == "GET" and path.startswith("/users/name/"):
            return {"id": self.user_ids[path.rsplit("/", 1)[1]]}
        if method == "PATCH":
            assert content_type == "application/json-patch+json"
            assert body[0]["op"] == "add" and body[0]["path"] == "/roles"
            self.user_roles[path.rsplit("/", 1)[1]] = body[0]["value"]
            return {}
        raise AssertionError(f"unexpected call {method} {path}")


def test_the_viewer_policy_allows_viewing_and_denies_every_change():
    view, deny = init.VIEWER_POLICY["rules"]
    assert (view["effect"], view["resources"], view["operations"]) == (
        "allow",
        ["all"],
        ["ViewAll"],
    )
    assert (deny["effect"], deny["resources"]) == ("deny", ["all"])
    assert set(deny["operations"]) == {
        "EditAll", "Create", "BulkCreate", "BulkUpdate", "Delete", "CreateTests",
        "CreateIngestionPipelineAutomator", "CreateTask", "ResolveTask", "CloseTask",
        "ReassignTask", "DeleteTestCaseFailedRowsSample", "Deploy", "Trigger", "Kill",
        "GenerateToken",
    }  # fmt: skip
    assert init.VIEWER_ROLE["policies"] == ["ViewerPolicy"]


def test_the_steward_gets_data_steward_and_the_viewer_gets_viewer():
    server = FakeServer()
    assert init.set_roles(server, lambda _: None) == {
        "steward": ["DataSteward"],
        "viewer": ["Viewer"],
    }
    assert server.policies == {"ViewerPolicy": init.VIEWER_POLICY}
    assert server.user_roles == {
        "id-steward": [{"id": "id-ds", "type": "role"}],
        "id-viewer": [{"id": "id-Viewer", "type": "role"}],
    }


def test_a_rerun_changes_nothing():
    server = FakeServer()
    init.set_roles(server, lambda _: None)
    state = (dict(server.policies), dict(server.roles), dict(server.user_roles))
    first = len(server.calls)
    assert init.set_roles(server, lambda _: None) == {
        "steward": ["DataSteward"],
        "viewer": ["Viewer"],
    }
    assert (server.policies, server.roles, server.user_roles) == state
    assert server.calls[first:] == server.calls[:first]


def test_a_server_that_refuses_each_call_is_tried_again():
    calls = len(init.ROLES) * 4 + 2
    for fail_at in range(calls):
        server = FakeServer(fail_at=fail_at)
        waits = []
        assert init.set_roles(server, waits.append) is None, fail_at
        assert len(waits) == init.TRIES - 1


def test_a_server_that_refuses_a_call_once_is_set_on_the_next_try():
    server = FakeServer(fail_at=3, failing_runs=1)
    waits = []
    result = init.set_roles(server, waits.append)
    assert result == {"steward": ["DataSteward"], "viewer": ["Viewer"]}
    assert waits == [5]


def test_every_admin_login_refused_sets_no_roles():
    api = FakeApi(refused=tuple(init.LOGINS))
    assert init.set_roles(api, lambda _: None) is None
    assert [p for _, p, _ in api.calls] == ["/users/login"] * len(init.LOGINS)
