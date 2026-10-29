"""Turns OpenMetadata's AutoPilot on or off, as METADATA_AUTOPILOT says.

The `openmetadata-init` service runs this once on every start of the `metadata`
profile. AutoPilot is the app that creates and runs default agents for a service
added in the UI. It does nothing while its `appConfiguration.active` is false, and
the UI does not change that value. The script logs in as `admin`, writes the
value, asks the server to apply it, reads it back and prints it. A database from
an earlier release keeps its `admin@open-data.local` user, so the script tries that
address when `admin@odctl.io` is refused.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

SERVER = "http://openmetadata-server:8585/api/v1"
APP = "AutoPilotApplication"
EMAILS = ("admin@odctl.io", "admin@open-data.local")
PASSWORD = "admin"
TRIES = 12
RETRY_SECONDS = 5
# 2.0.7: an unknown email gives 400 (BasicAuthenticator.lookUserInProvider); a wrong
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
    """Log in as admin with the first address the server accepts.

    Args:
        call (Callable[..., Any]): Sends one API request.

    Returns:
        Optional[str]: The JWT, or None when the server refused every address.

    Raises:
        urllib.error.URLError: When the server is not ready, so the caller tries again.
    """
    password = base64.b64encode(PASSWORD.encode()).decode()
    for email in EMAILS:
        try:
            reply = call("POST", "/users/login", {"email": email, "password": password})
            return reply["accessToken"]
        except urllib.error.HTTPError as error:
            if error.code not in REFUSED:
                raise
            print(f"{email} was refused: HTTP {error.code}", flush=True)
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


def main() -> None:
    """Apply METADATA_AUTOPILOT and print the result.

    It exits 0 even when the value could not be set, because the ingestion container
    waits for this service to complete, and a wrong admin password must not stop it.
    """
    active = wanted(os.environ.get("METADATA_AUTOPILOT", "false"))
    result = apply(active)
    if result is None:
        print("AutoPilot could not be set", flush=True)
        return
    print(f"AutoPilot active: {str(result).lower()}", flush=True)


if __name__ == "__main__":
    main()
