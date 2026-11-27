"""Sets OpenMetadata's AutoPilot and the roles of the two users who are not admins.

The `openmetadata-init` service runs this once on every start of the `metadata`
profile. AutoPilot is the app that creates and runs default agents for a service
added in the UI. It does nothing while its `appConfiguration.active` is false, and
the UI does not change that value. The script logs in as `admin`, writes the
value from METADATA_AUTOPILOT, asks the server to apply it, reads it back and
prints it. A database from an earlier release keeps the admin it was created
with, so the script tries each login in LOGINS in turn until the server accepts
one.

The server creates `steward` and `viewer` at start from AUTHORIZER_TEST_PRINCIPALS,
with no role of their own. The script then creates the read-only Viewer role,
gives `steward` the built-in DataSteward role and `viewer` the Viewer role, reads
the roles back and prints them.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, NamedTuple, Optional


class Login(NamedTuple):
    """One admin email and password the server may accept."""

    email: str
    password: str


SERVER = "http://openmetadata-server:8585/api/v1"
APP = "AutoPilotApplication"
# A new database from 1.7.0 on; a database from 1.3.0 to 1.6.0; one from before 1.3.0.
LOGINS = (
    Login("admin@odctl.io", "password"),
    Login("admin@odctl.io", "admin"),
    Login("admin@open-data.local", "admin"),
)
# Each user that is not an admin, and the role it gets.
ROLES = {"steward": "DataSteward", "viewer": "Viewer"}
VIEWER_POLICY = {
    "name": "ViewerPolicy",
    "description": "Read only: view everything, change nothing.",
    "rules": [
        {
            "name": "ViewerPolicy-ViewRule",
            "resources": ["all"],
            "operations": ["ViewAll"],
            "effect": "allow",
        },
        # Every user also takes DataConsumer from the Organization team, which may
        # edit descriptions and tags and create tasks. Deny rules are checked first,
        # and EditAll matches every Edit operation.
        {
            "name": "ViewerPolicy-DenyRule",
            "resources": ["all"],
            "operations": [
                "EditAll",
                "Create",
                "BulkCreate",
                "BulkUpdate",
                "Delete",
                "CreateTests",
                "CreateIngestionPipelineAutomator",
                "CreateTask",
                "ResolveTask",
                "CloseTask",
                "ReassignTask",
                "DeleteTestCaseFailedRowsSample",
                "Deploy",
                "Trigger",
                "Kill",
                "GenerateToken",
            ],
            "effect": "deny",
        },
    ],
}
VIEWER_ROLE = {
    "name": "Viewer",
    "description": "Read only, for the viewer login.",
    "policies": ["ViewerPolicy"],
}
TRIES = 12
RETRY_SECONDS = 5
# 2.0.8: an unknown email gives 400 (BasicAuthenticator.lookUserInProvider); a wrong
# password or a blocked login gives 401 (AuthenticationException).
REFUSED = (400, 401)


def _call(
    method: str,
    path: str,
    body: Any = None,
    token: Optional[str] = None,
    content_type: str = "application/json",
) -> Any:
    """Send one request to the OpenMetadata API.

    Args:
        method (str): The HTTP method.
        path (str): The path below `/api/v1`.
        body (Any): The JSON body, or None for no body.
        token (Optional[str]): The JWT to send, or None before the login.
        content_type (str): The body's media type.

    Returns:
        Any: The decoded JSON reply, or None when the reply has no body.

    Raises:
        urllib.error.URLError: When the server cannot be reached or answers an error.
    """
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{SERVER}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=30) as reply:
        text = reply.read().decode()
    try:
        return json.loads(text)
    except ValueError:
        return None


def _login(call: Callable[..., Any]) -> Optional[str]:
    """Log in as admin with the first login the server accepts.

    Args:
        call (Callable[..., Any]): Sends one API request.

    Returns:
        Optional[str]: The JWT, or None when the server refused every login.

    Raises:
        urllib.error.URLError: When the server is not ready, so the caller tries again.
    """
    for number, login in enumerate(LOGINS, start=1):
        password = base64.b64encode(login.password.encode()).decode()
        try:
            reply = call(
                "POST", "/users/login", {"email": login.email, "password": password}
            )
            return reply["accessToken"]
        except urllib.error.HTTPError as error:
            if error.code not in REFUSED:
                raise
            print(
                f"Login {number} of {len(LOGINS)} ({login.email}) was refused:"
                f" HTTP {error.code}",
                flush=True,
            )
    return None


def wanted(value: str) -> bool:
    """Read the setting: only the word `true` turns AutoPilot on.

    Args:
        value (str): The value of METADATA_AUTOPILOT.

    Returns:
        bool: True when AutoPilot is to be on.
    """
    return value.strip().lower() == "true"


def apply(
    active: bool,
    call: Callable[..., Any] = _call,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[bool]:
    """Set AutoPilot's `active` value, trying again while the server is not ready.

    Args:
        active (bool): The value to set.
        call (Callable[..., Any]): Sends one API request.
        sleep (Callable[[float], None]): Waits between tries.

    Returns:
        Optional[bool]: The value the server reports after the change, or None when
        no try worked or the server refused every admin address.
    """
    for attempt in range(TRIES):
        try:
            token = _login(call)
            if token is None:
                return None
            patch = [{"op": "add", "path": "/appConfiguration/active", "value": active}]
            call(
                "PATCH",
                f"/apps/name/{APP}",
                patch,
                token,
                "application/json-patch+json",
            )
            call("POST", f"/apps/configure/{APP}", None, token)
            app = call("GET", f"/apps/name/{APP}?fields=appConfiguration", None, token)
            return app["appConfiguration"]["active"]
        except Exception as error:
            print("Setting AutoPilot failed:", error, flush=True)
            if attempt < TRIES - 1:
                sleep(RETRY_SECONDS)
    return None


def _set_roles(call: Callable[..., Any], token: str) -> dict[str, list[str]]:
    """Create the Viewer role and give each user in ROLES its role.

    PUT creates the policy and the role or updates them to the same value, and the
    patch replaces the user's roles, so a rerun changes nothing.

    Args:
        call (Callable[..., Any]): Sends one API request.
        token (str): An admin's JWT.

    Returns:
        dict[str, list[str]]: Each user's role names, read back from the server.
    """
    call("PUT", "/policies", VIEWER_POLICY, token)
    call("PUT", "/roles", VIEWER_ROLE, token)
    result = {}
    for user, role in ROLES.items():
        role_id = call("GET", f"/roles/name/{role}", None, token)["id"]
        user_id = call("GET", f"/users/name/{user}", None, token)["id"]
        patch = [
            {"op": "add", "path": "/roles", "value": [{"id": role_id, "type": "role"}]}
        ]
        call("PATCH", f"/users/{user_id}", patch, token, "application/json-patch+json")
        reply = call("GET", f"/users/name/{user}?fields=roles", None, token)
        result[user] = [r["name"] for r in reply.get("roles") or []]
    return result


def set_roles(
    call: Callable[..., Any] = _call,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[dict[str, list[str]]]:
    """Set the users' roles, trying again while the server is not ready.

    Args:
        call (Callable[..., Any]): Sends one API request.
        sleep (Callable[[float], None]): Waits between tries.

    Returns:
        Optional[dict[str, list[str]]]: Each user's role names, or None when no try
        worked or the server refused every admin address.
    """
    for attempt in range(TRIES):
        try:
            token = _login(call)
            if token is None:
                return None
            return _set_roles(call, token)
        except Exception as error:
            print("Setting the roles failed:", error, flush=True)
            if attempt < TRIES - 1:
                sleep(RETRY_SECONDS)
    return None


def main() -> None:
    """Apply METADATA_AUTOPILOT, set the users' roles and print the results.

    It exits 0 even when a value could not be set, because the ingestion container
    waits for this service to complete, and a wrong admin password must not stop it.
    """
    active = wanted(os.environ.get("METADATA_AUTOPILOT", "false"))
    result = apply(active)
    if result is None:
        print("AutoPilot could not be set", flush=True)
    else:
        print(f"AutoPilot active: {str(result).lower()}", flush=True)
    roles = set_roles()
    if roles is None:
        print("The users' roles could not be set", flush=True)
        return
    for user, names in roles.items():
        print(f"{user} roles: {', '.join(names) or 'none'}", flush=True)


if __name__ == "__main__":
    main()
