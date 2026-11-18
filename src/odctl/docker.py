import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from python_on_whales import DockerClient

from odctl.config import get_active_dir, get_compose_path, read_yaml


def create_client(
    compose_file: str | None = None, profiles: List[str] | None = None
) -> DockerClient:
    """
    Create a Docker client that naturally honors the system's Docker context.

    A client for a compose file runs it as the project `get_project_name` names, so
    a COMPOSE_PROJECT_NAME in the shell or in `.env` cannot merge every file into one
    project: `--project-name` takes precedence over it (Docker docs, "Specify a
    project name").

    Args:
        compose_file (str, optional): The name of the compose file, such as
            'compose-kafka.yml'. Defaults to None, for a client with no project.
        profiles (List[str], optional): A list of compose profiles to activate. Defaults to None.

    Returns:
        DockerClient: An initialized python-on-whales Docker client.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    kwargs: Dict[str, Any] = {}

    if "DOCKER_HOST" in os.environ:
        kwargs["host"] = os.environ["DOCKER_HOST"]

    if compose_file:
        kwargs["compose_files"] = [str(get_compose_path(compose_file))]
        kwargs["compose_project_name"] = get_project_name(compose_file)

    if profiles:
        kwargs["compose_profiles"] = profiles

    return DockerClient(**kwargs)


# Global client used for basic checks
client = create_client()


def is_docker_running() -> bool:
    """
    Check if the Docker daemon is reachable.

    Returns:
        bool: True if the Docker engine responds to system info requests, False otherwise.
    """
    try:
        # Changed from client.ping() to client.system.info()
        client.system.info()
        return True
    except Exception:
        return False


def read_compose(compose_filename: str) -> Dict[str, Any]:
    """
    Read a compose file of the active directory.

    Args:
        compose_filename (str): The name of the compose file, such as 'compose-kafka.yml'.

    Returns:
        Dict[str, Any]: The file's content. Its `services` entry, when present, maps
        each service name to a mapping.

    Raises:
        ValueError: As `Cannot read <file>: <reason>`, when the file is missing, is not
            valid YAML, or its top level, its services or one of them is not a mapping.
    """
    compose = read_yaml(get_compose_path(compose_filename), compose_filename)
    if not isinstance(compose, dict):
        raise ValueError(
            f"Cannot read {compose_filename}: its top level is not a mapping."
        )
    services = compose.get("services") or {}
    if not isinstance(services, dict):
        raise ValueError(
            f"Cannot read {compose_filename}: its services are not a mapping."
        )
    for name, service in services.items():
        if not isinstance(service, dict):
            raise ValueError(
                f"Cannot read {compose_filename}: the service '{name}' is not a mapping."
            )
    return compose


def get_project_name(compose_filename: str) -> str:
    """
    Name the Compose project a compose file runs as, as Compose names it.

    That is the file's top-level `name:`, interpolated, or without one the name of
    the folder that holds the file. Compose then lower-cases it, keeps only a-z,
    0-9, `_` and `-`, and trims `_` and `-` from the start (compose-go
    loader/loader.go, `projectName` and `NormalizeProjectName`).

    Args:
        compose_filename (str): The name of the compose file.

    Returns:
        str: The project name.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose = read_compose(compose_filename)
    name = expand(str(compose.get("name") or ""), interpolation_env())
    name = name or get_compose_path(compose_filename).parent.name
    return re.sub(r"[^a-z0-9_-]", "", name.lower()).lstrip("_-")


def get_stack_details(
    compose_filename: str, profiles: List[str]
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Resolve services, host port mappings, images, and volumes via direct YAML parsing.

    A service with no `profiles` belongs to every profile of its file, because
    Compose starts it whatever profiles are active.

    Args:
        compose_filename (str): The name of the compose file to parse.
        profiles (List[str]): The active profiles to filter services by.

    Returns:
        Tuple[List[str], List[str], List[str], List[str]]: A tuple containing four sorted lists:
            services, exposed host ports, container images, and named volumes.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose_dict = read_compose(compose_filename)
    env = interpolation_env()

    services = []
    ports = []
    images = []
    volumes = []

    # Parse the raw dictionary directly
    for svc_name, svc_data in (compose_dict.get("services") or {}).items():
        svc_profiles = svc_data.get("profiles")

        # Check if this service belongs to the profiles we are querying
        if not svc_profiles or any(p in profiles for p in svc_profiles):
            services.append(svc_name)

            if "image" in svc_data:
                # Shown as it will run: `${TAG:-latest}` resolves the way compose
                # resolves it, which is the CLI version without a workspace.
                image = expand(svc_data["image"], interpolation_env())
                images.append(f"{svc_name} -> {image}")

            if "ports" in svc_data:
                for p in svc_data["ports"]:
                    if isinstance(p, str):
                        ports.append(f"{svc_name}:{p}")
                    elif isinstance(p, dict) and "published" in p:
                        target = p.get("target", p["published"])
                        protocol = f"/{p['protocol']}" if p.get("protocol") else ""
                        ports.append(f"{svc_name}:{p['published']}:{target}{protocol}")

            if "volumes" in svc_data:
                for v in svc_data["volumes"]:
                    if isinstance(v, str):
                        # Compose interpolates the entry before it splits it, so
                        # `${PG_VOLUME:-pgdata}:/data` mounts the volume `pgdata`.
                        vol_name = expand(v, env).split(":")[0]
                        # Only track named volumes, ignore local host bind mounts (./, / or ~)
                        if not vol_name.startswith((".", "/", "~")):
                            volumes.append(vol_name)
                    elif isinstance(v, dict) and v.get("type") == "volume":
                        source = v.get("source")
                        if isinstance(source, str):
                            volumes.append(source)

    # Drop volumes the file declares as external. Compose never removes
    # those, so mounting one is not a reason to tear a profile down. Counting
    # them made `odctl down --all --volumes` select `catalog` purely because
    # it mounts the shared dependency volume, even when nothing of it ran.
    declared = compose_dict.get("volumes") or {}
    external = {
        name
        for name, spec in declared.items()
        if isinstance(spec, dict) and spec.get("external")
    }
    volumes = [v for v in volumes if v not in external]

    return (
        sorted(list(set(services))),
        sorted(list(set(ports))),
        sorted(list(set(images))),
        sorted(list(set(volumes))),
    )


# Images this project builds and publishes itself. They carry the CLI version as
# their tag, so a version whose build has not finished has no image to pull.
# Every other image in the compose files is a third-party one pinned to an exact
# upstream version, and those are never checked here.
ODCTL_IMAGE_PREFIX = "ghcr.io/jaehyeon-kim/odctl/"

# Compose interpolation, in every form the Compose specification and Docker's docs
# list, because a workspace file may use any of them: $VAR, ${VAR}, the operators
# :- - :? ? :+ +, a word that holds another reference, and $$ for a literal $.
_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BRACED_REFERENCE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:(:?[-?+])(.*))?", re.S)

# Registry replies that mean the tag is genuinely absent. Anything else, a DNS
# failure, a refused connection or a missing credential helper for instance,
# leaves the answer unknown, and an unknown answer must not stop a launch.
_ABSENT_MARKERS = ("manifest unknown", "no such manifest")


# What compose-go's dotenv parser treats as a space within a line (`isSpace` in
# dotenv/parser.go): every space character but the line break.
_ENV_SPACES = "\t\v\f\r \x85\xa0"

# The escapes Compose applies in a double-quoted value (`escapeSeqRegex`).
_ENV_ESCAPE = re.compile(r'\\(?:[abcfnrtv$"\\]|0\d{0,3})')
_ENV_ESCAPED = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "$": "$$",
    '"': '"',
    "\\": "\\",
}


class _EnvLineError(Exception):
    """A statement of a `.env` file that Compose rejects."""


def _env_escape(match: re.Match) -> str:
    """
    Apply one escape of a double-quoted `.env` value, as `expandEscapes` does.

    Args:
        match (re.Match): A match of `_ENV_ESCAPE`.

    Returns:
        str: The character. `\\$` gives `$$`, which interpolation turns into `$`. An
        octal escape needs `\\0` and three octal digits; any other is kept as written.
    """
    text = match.group(0)
    if text[1] != "0":
        return _ENV_ESCAPED[text[1]]
    digits = text[2:]
    if len(digits) == 3 and all(d in "01234567" for d in digits):
        if int(digits, 8) <= 0o377:
            return chr(int(digits, 8))
    return text


def _env_key(src: str) -> Tuple[str, str, bool]:
    """
    Read the key that starts a `.env` statement, as `locateKeyName` does.

    Args:
        src (str): The file from the start of the statement.

    Returns:
        Tuple[str, str, bool]: The key; the text after its `=`, `:` or line break, with
        the spaces before the value removed; and True when the key stands alone on
        its line, so its value comes from the environment.

    Raises:
        _EnvLineError: When the key holds a character other than letters, digits,
            `_`, `.`, `-`, `[` and `]`.
    """
    if re.match(r"export[\t\n\f\r ]", src):
        src = src[len("export") :].lstrip(_ENV_SPACES)
    for index, char in enumerate(src):
        if char in _ENV_SPACES:
            continue
        if char in "=:\n":
            rest = src[index + 1 :].lstrip(_ENV_SPACES)
            return src[:index].rstrip(), rest, char == "\n"
        if not (char in "_.-[]" or char.isalpha() or char.isnumeric()):
            raise _EnvLineError(char)
    return src.rstrip(), "", True


def _env_value(src: str, env: Dict[str, str]) -> Tuple[str, str]:
    """
    Read the value of a `.env` statement, as `extractVarValue` does.

    An unquoted value ends at the line break, loses an inline comment that follows a
    space, and is interpolated. A single-quoted value is kept as written, and a
    double-quoted one gets its escapes and is interpolated; both can span lines,
    and a backslash before the quote keeps it in the value.

    Args:
        src (str): The file from the start of the value.
        env (Dict[str, str]): The variables interpolation reads.

    Returns:
        Tuple[str, str]: The value, and the text after it.

    Raises:
        _EnvLineError: When a quoted value has no closing quote.
    """
    if not src or src[0] not in "\"'":
        value, _, rest = src.partition("\n")
        value = value.split(" #", 1)[0].rstrip()
        return expand(value, env), rest

    quote = src[0]
    chars = []
    escaped = False
    for index in range(1, len(src)):
        char = src[index]
        if char != quote:
            if not escaped and char == "\\":
                escaped = True
                continue
            if escaped:
                escaped = False
                chars.append("\\")
            chars.append(char)
            continue
        if escaped:
            escaped = False
            chars.append(char)
            continue
        value = "".join(chars)
        if quote == '"':
            value = expand(_ENV_ESCAPE.sub(_env_escape, value), env)
        return value, src[index + 1 :]
    raise _EnvLineError(quote)


def _read_env_file(path: Path) -> Dict[str, str]:
    """
    Parse a compose `.env` file into a plain dictionary, as Compose reads it.

    The rules are those of compose-go's dotenv parser (dotenv/parser.go), the code
    Compose runs. `#` starts a comment line. A key is followed by `=` or `:`, and
    `export ` before it is dropped. A later line overrides an earlier one. Values
    are read by `_env_value`, and interpolation reads the shell environment first,
    then the lines above (dotenv/godotenv.go, `expandVariables`). A key alone on
    its line takes its value from the shell environment. Compose stops at a line it
    rejects; odctl reads the file only to show and check what Compose will run, so
    it skips that line and reads on, and Compose reports the line when it runs.

    Args:
        path (Path): Path to the `.env` file. A missing file yields an empty mapping.

    Returns:
        Dict[str, str]: The declared variables, with their values as Compose reads them.
    """
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    src = path.read_text()
    while True:
        src = src.lstrip()
        while src.startswith("#"):
            _, newline, src = src.partition("\n")
            src = src.lstrip() if newline else ""
        if not src:
            return values
        try:
            key, rest, inherited = _env_key(src)
            if not key or " " in key:
                raise _EnvLineError(key)
            if inherited:
                if key in os.environ:
                    values[key] = os.environ[key]
            else:
                values[key], rest = _env_value(rest, {**values, **os.environ})
            src = rest
        except _EnvLineError:
            src = src.partition("\n")[2]


def interpolation_env() -> Dict[str, str]:
    """
    Build the variable mapping compose uses to interpolate the compose files.

    Compose reads `.env` from the project directory, which is the directory
    holding the compose file, and lets the shell environment override it.

    Returns:
        Dict[str, str]: Variables from the active directory's `.env`, overridden
        by the current process environment.
    """
    env = _read_env_file(get_active_dir() / ".env")
    env.update(os.environ)
    return env


def expand(value: str, env: Dict[str, str]) -> str:
    """
    Substitute compose variables in a string.

    Args:
        value (str): A raw value from a compose file, such as an image reference.
        env (Dict[str, str]): The variables to substitute.

    Returns:
        str: The value with every variable reference replaced. A reference that is
            not valid Compose syntax is kept as written.
    """
    parts = []
    i = 0
    while i < len(value):
        if value[i] != "$":
            parts.append(value[i])
            i += 1
        elif value.startswith("$$", i):
            parts.append("$")
            i += 2
        elif value.startswith("${", i):
            end = _closing_brace(value, i + 2)
            if end is None:
                parts.append(value[i:])
                break
            parts.append(_substitute(value[i + 2 : end], env))
            i = end + 1
        elif name := _VARIABLE_NAME.match(value, i + 1):
            parts.append(env.get(name.group(0)) or "")
            i = name.end()
        else:
            parts.append("$")
            i += 1
    return "".join(parts)


def _closing_brace(value: str, start: int) -> Optional[int]:
    """
    Find the brace that closes a `${` reference, past any reference nested in it.

    Args:
        value (str): The string being expanded.
        start (int): The index just after the opening `${`.

    Returns:
        Optional[int]: The index of the closing brace, or None when there is none.
    """
    depth = 1
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _substitute(reference: str, env: Dict[str, str]) -> str:
    """
    Return the value of one braced reference, the text between `${` and `}`.

    The `:?` and `?` forms make Compose stop with an error when they do not hold.
    odctl only shows the value, so it shows an empty one instead.

    Args:
        reference (str): The name, then optionally an operator and its word.
        env (Dict[str, str]): The variables to substitute.

    Returns:
        str: The value the operator selects. The word is expanded too, so it can
            hold another reference.
    """
    match = _BRACED_REFERENCE.fullmatch(reference)
    if not match:
        return "${" + reference + "}"
    name, operator, word = match.groups()
    current = env.get(name)
    # The operators with a colon test for a non-empty value, the others for a set one.
    holds = (
        bool(current) if operator is None or ":" in operator else current is not None
    )
    if operator in (None, ":?", "?"):
        return (current or "") if holds else ""
    if operator in (":-", "-"):
        return (current or "") if holds else expand(word, env)
    return expand(word, env) if holds else ""


def resolve_image_tag() -> str:
    """
    Resolve the tag the compose files will put on the images odctl builds.

    Returns:
        str: The value of TAG as compose resolves it, or 'latest' when unset.
    """
    return expand("${TAG:-latest}", interpolation_env())


def get_versioned_images(execution_plan: Dict[str, List[str]]) -> List[str]:
    """
    List the version-coupled image references an execution plan needs.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[str]: Sorted, deduplicated references to images built by this
        project, with their variables already substituted.
    """
    env = interpolation_env()
    references = set()

    for file, profiles in execution_plan.items():
        _, _, images, _ = get_stack_details(file, profiles)
        for entry in images:
            _, _, raw = entry.partition(" -> ")
            reference = expand(raw, env)
            if reference.startswith(ODCTL_IMAGE_PREFIX):
                references.add(reference)

    return sorted(references)


def image_is_local(reference: str) -> bool:
    """
    Report whether an image is already on the Docker host.

    Args:
        reference (str): A full image reference.

    Returns:
        bool: True when the local daemon holds the image.
    """
    try:
        return bool(client.image.exists(reference))
    except Exception:
        return False


def _registry_has_image(reference: str) -> Optional[bool]:
    """
    Ask the registry whether an image tag is published.

    Args:
        reference (str): A full image reference.

    Returns:
        Optional[bool]: True when the registry serves a manifest for it, False
        when the registry says the tag is absent, and None when the question
        could not be answered, which is what an offline machine returns.
    """
    try:
        client.manifest.inspect(reference)
        return True
    except Exception as exc:
        text = f"{getattr(exc, 'stderr', '') or ''} {exc}".lower()
        if any(marker in text for marker in _ABSENT_MARKERS):
            return False
        return None


def find_unpublished_images(execution_plan: Dict[str, List[str]]) -> List[str]:
    """
    Find images an execution plan needs that neither Docker nor the registry has.

    An image already on the host is accepted without a registry call, so a
    machine with no network can still start a stack it has pulled before. A
    registry that cannot be reached leaves the answer unknown, and an unknown
    answer is treated as present so the launch proceeds and Docker reports
    whatever it finds.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    Returns:
        List[str]: References the registry reported as absent, in sorted order.
    """
    candidates = [
        reference
        for reference in get_versioned_images(execution_plan)
        if not image_is_local(reference)
    ]
    if not candidates:
        return []

    # Each registry call is a network round trip of a second or more, so ask
    # about every image at once rather than one after another.
    with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
        answers = list(pool.map(_registry_has_image, candidates))

    return [
        reference for reference, answer in zip(candidates, answers) if answer is False
    ]


def pull_stack_images(compose_filename: str, profiles: List[str]):
    """
    Pull required images for a specific stack.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles indicating which services to pull.
    """
    stack_client = create_client(compose_filename, profiles)
    stack_client.compose.pull()


# Containers that do one job and exit, such as creating the SeaweedFS buckets.
# `docker compose up --wait` fails when a container it finds running exits during
# the wait, even with code 0. `recreate storage` returns while seaweed-init is
# still creating buckets, so an `up` straight after it failed until it finished.
_ONE_SHOT_CONTAINERS = ("seaweed-init",)


def wait_for_one_shot_containers():
    """Block until any one-shot container that is still running has exited."""
    for name in _ONE_SHOT_CONTAINERS:
        if (
            client.container.exists(name)
            and client.container.inspect(name).state.running
        ):
            client.container.wait(name)


def launch_stack(compose_filename: str, profiles: List[str]):
    """
    Start the stack via docker compose up.

    If the 'deps' profile is active, this blocks until the ephemeral init container
    finishes. Otherwise, it detaches and waits for healthchecks.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to launch.
    """
    stack_client = create_client(compose_filename, profiles)

    # The 'deps' profile contains an ephemeral container that exits after copying files.
    # Docker Compose's --wait flag fails if it sees a container exit (even with code 0).
    if "deps" in profiles:
        # detach=False blocks until the init container gracefully finishes its job
        stack_client.compose.up(detach=False)
    else:
        # For all other long-running services, we detach and wait for healthchecks
        wait_for_one_shot_containers()
        stack_client.compose.up(detach=True, wait=True)


def stop_stack(
    compose_filename: str, profiles: List[str], remove_volumes: bool = False
):
    """
    Stop and remove containers and networks for a stack.

    Args:
        compose_filename (str): The compose file defining the target stack.
        profiles (List[str]): The profiles to stop.
        remove_volumes (bool, optional): If True, destroys the named volumes of the
                                         stack and the unnamed volumes of its
                                         containers. Defaults to False.
    """
    stack_client = create_client(compose_filename, profiles)
    # volumes=True removes the named volumes defined in the compose file and the
    # unnamed volumes of the containers it stops.
    # remove_orphans catches containers whose service no longer exists in the
    # compose file, which teardown would otherwise leave running forever: an
    # upgrade that drops or renames a service (ch-init-lite in 0.2.0, the
    # flink1-* services in 0.3.0) leaves the old container holding its name.
    stack_client.compose.down(volumes=remove_volumes, remove_orphans=True)


def get_declared_volumes(compose_filename: str) -> Dict[str, str]:
    """
    Map each volume a compose file declares, external ones too, to its Docker name.

    A service mounts a volume by its key, and Docker lists it by its name. A mount
    of one of these is a named volume. Any other volume a container mounts is an
    unnamed one, which Docker creates from the image's `VOLUME` line.

    The name is the entry's `name:`, interpolated as Compose does, because a
    workspace file can build it from variables. Without `name:`, Compose names the
    volume `<project>_<key>`, from the file's top-level `name:`, or `<key>` when
    the volume is external.

    Args:
        compose_filename (str): The name of the compose file to parse.

    Returns:
        Dict[str, str]: Each volume's key to its Docker name.

    Raises:
        ValueError: If the compose file cannot be read.
    """
    compose = read_compose(compose_filename)
    env = interpolation_env()
    project = expand(str(compose.get("name") or ""), env)
    names = {}
    for key, spec in (compose.get("volumes") or {}).items():
        name = spec.get("name") if isinstance(spec, dict) else None
        external = isinstance(spec, dict) and spec.get("external")
        if name:
            names[key] = expand(str(name), env)
        elif external or not project:
            names[key] = key
        else:
            names[key] = f"{project}_{key}"
    return names


def get_volume_names() -> set:
    """
    Fetch the names of the volumes that exist, as `docker volume ls` lists them.

    Returns:
        set: The volume names.
    """
    return {volume.name for volume in client.volume.list()}


def get_managed_containers(execution_plan: Dict[str, List[str]]) -> List[Any]:
    """
    Fetch Docker containers matching the requested execution plan.

    Args:
        execution_plan (Dict[str, List[str]]): A mapping of compose files to target profiles.

    A container counts when its Compose project is the project of one of the plan's
    files, as `get_project_name` names it, and its service is one of theirs. A
    workspace file can set its own `name:`, so the project need not start with
    `odctl-`.

    Returns:
        List[Any]: A list of python-on-whales Container objects managed by the ODCTL stack.

    Raises:
        ValueError: If a compose file of the plan cannot be read.
    """
    target_services = set()
    projects = set()
    for file, profs in execution_plan.items():
        # Re-using your existing parser to know exactly which services to look for
        services, _, _, _ = get_stack_details(file, profs)
        target_services.update(services)
        projects.add(get_project_name(file))

    all_containers = client.container.list(all=True)
    managed_containers = []

    for c in all_containers:
        # Safely access labels via the Container's Config block
        labels = c.config.labels if c.config and c.config.labels else {}

        project = labels.get("com.docker.compose.project", "")
        service = labels.get("com.docker.compose.service", "")

        # Strictly enforce that the container belongs to a ODCTL stack AND the requested profile
        if project in projects and service in target_services:
            managed_containers.append(c)

    return managed_containers
