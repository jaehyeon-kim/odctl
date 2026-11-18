import pytest
from unittest.mock import MagicMock

from odctl import docker


def test_is_docker_running_success(monkeypatch):
    mock_client = MagicMock()
    mock_client.system.info.return_value = {}
    monkeypatch.setattr(docker, "client", mock_client)
    assert docker.is_docker_running() is True


def test_is_docker_running_fail(monkeypatch):
    mock_client = MagicMock()
    mock_client.system.info.side_effect = Exception("error")
    monkeypatch.setattr(docker, "client", mock_client)
    assert docker.is_docker_running() is False


def test_get_stack_details(tmp_path, monkeypatch):
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  test-service:
    image: test-image:latest
    profiles: ["prof1"]
    ports:
      - "8080:80"
    volumes:
      - my-vol:/data
  test-service-2:
    profiles: ["prof2"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)

    services, ports, images, volumes = docker.get_stack_details(
        "compose-test.yml", ["prof1"]
    )
    assert services == ["test-service"]
    assert ports == ["test-service:8080:80"]
    assert images == ["test-service -> test-image:latest"]
    assert volumes == ["my-vol"]


@pytest.mark.parametrize(
    "text, reason",
    [
        (None, "the file does not exist"),
        ("services: [\n", "it is not valid YAML"),
        ("", "its top level is not a mapping"),
        ("- a\n- b\n", "its top level is not a mapping"),
        ("services:\n  - a\n", "its services are not a mapping"),
        ("services:\n  a:\n", "the service 'a' is not a mapping"),
    ],
    ids=["missing", "invalid", "empty", "list", "services list", "service null"],
)
def test_an_unreadable_compose_file_raises_one_error(
    tmp_path, monkeypatch, text, reason
):
    """Every reader of a compose file stops with the same message, which names the
    file and the reason, where it used to return an error marker as data or raise
    the error of the YAML parser."""
    compose_path = tmp_path / "compose-test.yml"
    if text is not None:
        compose_path.write_text(text)
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    for read in (
        lambda: docker.get_stack_details("compose-test.yml", ["prof1"]),
        lambda: docker.get_declared_volumes("compose-test.yml"),
        lambda: docker.get_versioned_images({"compose-test.yml": ["prof1"]}),
    ):
        with pytest.raises(
            ValueError, match=f"^Cannot read compose-test.yml: {reason}"
        ):
            read()


def test_a_short_volume_is_read_after_interpolation(tmp_path, monkeypatch):
    """Compose interpolates a mount before it splits it, and a source that starts with
    `~` is a bind mount, as with `.` and `/` (Docker docs, "Volumes" in the services
    top-level element: a source that is a path is a bind mount)."""
    compose_path = tmp_path / "compose-x.yml"
    compose_path.write_text(
        "name: odctl-x\nservices:\n  db:\n    image: postgres:17\n    profiles: [x]\n"
        "    volumes:\n      - ${PG_VOLUME:-pgdata}:/var/lib/postgresql/data\n"
        "      - ~/backups:/backups\nvolumes:\n  pgdata: {}\n"
    )
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("PG_VOLUME", raising=False)

    keys = docker.get_stack_details("compose-x.yml", ["x"])[3]
    declared = docker.get_declared_volumes("compose-x.yml")
    # The names the dry run of `down --volumes` prints, as `_dry_run_volumes` builds them.
    assert [declared.get(key, key) for key in keys] == ["odctl-x_pgdata"]


def test_a_service_without_profiles_belongs_to_every_profile(tmp_path, monkeypatch):
    """Compose starts a service with no `profiles` key whatever profiles are active
    (Docker docs, "Using profiles with Compose": services without a profiles
    attribute are always enabled)."""
    compose_path = tmp_path / "compose-x.yml"
    compose_path.write_text(
        "services:\n  a:\n    image: x:1\n    profiles: [x]\n  sidecar:\n    image: y:1\n"
    )
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    services = docker.get_stack_details("compose-x.yml", ["x"])[0]
    assert services == ["a", "sidecar"]


def test_docker_actions(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(docker, "create_client", lambda *a, **kw: mock_client)
    monkeypatch.setattr(docker, "wait_for_one_shot_containers", lambda: None)
    monkeypatch.setattr(docker, "get_compose_path", lambda x: "dummy.yml")

    docker.pull_stack_images("dummy.yml", ["prof1"])
    mock_client.compose.pull.assert_called_once()

    docker.launch_stack("dummy.yml", ["prof1"])
    mock_client.compose.up.assert_called_with(detach=True, wait=True)

    docker.launch_stack("dummy.yml", ["deps"])
    mock_client.compose.up.assert_called_with(detach=False)

    docker.stop_stack("dummy.yml", ["prof1"], remove_volumes=True)
    # remove_orphans is what clears containers whose service was dropped
    # from the compose file.
    mock_client.compose.down.assert_called_with(volumes=True, remove_orphans=True)


def _compose_named(tmp_path, monkeypatch, name):
    """Point every compose file at one with a single service and the given `name:`."""
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text(
        f"name: {name}\nservices:\n  test-service:\n    image: x:1\n    profiles: [prof1]\n"
    )
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)


def test_get_managed_containers(tmp_path, monkeypatch):
    _compose_named(tmp_path, monkeypatch, "odctl-test")

    mock_container = MagicMock()
    mock_container.config.labels = {
        "com.docker.compose.project": "odctl-test",
        "com.docker.compose.service": "test-service",
    }
    mock_ignored = MagicMock()
    mock_ignored.config.labels = {
        "com.docker.compose.project": "other-test",
        "com.docker.compose.service": "test-service",
    }
    mock_client = MagicMock()
    mock_client.container.list.return_value = [mock_container, mock_ignored]
    monkeypatch.setattr(docker, "client", mock_client)

    res = docker.get_managed_containers({"dummy.yml": ["prof1"]})
    assert len(res) == 1
    assert res[0] == mock_container


def test_a_workspace_file_with_its_own_project_name_is_managed(tmp_path, monkeypatch):
    """A workspace file whose `name:` the user changed is still odctl's: its
    containers count, where only projects named `odctl-...` counted before."""
    _compose_named(tmp_path, monkeypatch, "my-${TEAM:-x}")
    monkeypatch.setenv("TEAM", "flink")
    renamed = MagicMock()
    renamed.config.labels = {
        "com.docker.compose.project": "my-flink",
        "com.docker.compose.service": "test-service",
    }
    mock_client = MagicMock()
    mock_client.container.list.return_value = [renamed]
    monkeypatch.setattr(docker, "client", mock_client)

    assert docker.get_managed_containers({"dummy.yml": ["prof1"]}) == [renamed]


def test_each_client_names_its_project_from_its_file(tmp_path, monkeypatch):
    """`--project-name` takes precedence over COMPOSE_PROJECT_NAME, which would
    otherwise run every file as one project (Docker docs, "Specify a project
    name"). python-on-whales passes `compose_project_name` as `--project-name`
    (client_config.py, ClientConfig.docker_compose_cmd)."""
    _compose_named(tmp_path, monkeypatch, "odctl-kafka")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "demo")

    client = docker.create_client("compose-kafka.yml", ["kafka-lite"])

    command = list(client.client_config.docker_compose_cmd)
    assert command[command.index("--project-name") + 1] == "odctl-kafka"
    assert command[command.index("--file") + 1] == str(tmp_path / "compose-test.yml")


def test_a_file_without_a_name_gets_the_name_compose_gives_it(tmp_path, monkeypatch):
    """Without `name:`, Compose names the project after the folder of the file,
    lower-cased with every character other than a-z, 0-9, `_` and `-` removed, and
    `_` and `-` trimmed from the start (compose-go loader/loader.go,
    NormalizeProjectName)."""
    folder = tmp_path / "My.Work"
    folder.mkdir()
    compose_path = folder / "compose-test.yml"
    compose_path.write_text("services:\n  a:\n    image: x:1\n")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: folder)

    assert docker.get_project_name("compose-test.yml") == "mywork"


# ==========================================
# Preflight: images built by this project
# ==========================================

DEPS_IMAGE = "ghcr.io/jaehyeon-kim/odctl/deps"


class FakeDockerException(Exception):
    """A stand-in for python_on_whales' exception, which carries stderr."""

    def __init__(self, stderr: str):
        super().__init__("The command executed was `docker manifest inspect`.")
        self.stderr = stderr


def _preflight_plan(tmp_path, monkeypatch) -> dict:
    """Write a compose file holding one built image and one third-party image."""
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  init-deps:
    image: ghcr.io/jaehyeon-kim/odctl/deps:${TAG:-latest}
    profiles: ["prof1"]
  postgres:
    image: postgres:17.2
    profiles: ["prof1"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    return {"compose-test.yml": ["prof1"]}


def test_resolve_image_tag_reads_the_workspace_env_file(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("# Auto-generated\nTAG=1.2.3\nTZ=UTC\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("TAG", raising=False)

    assert docker.resolve_image_tag() == "1.2.3"


def test_resolve_image_tag_lets_the_shell_win(tmp_path, monkeypatch):
    """Compose gives the shell environment precedence over the .env file."""
    (tmp_path / ".env").write_text("TAG=1.2.3\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.setenv("TAG", "4.5.6")

    assert docker.resolve_image_tag() == "4.5.6"


def test_resolve_image_tag_falls_back_to_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("TAG", raising=False)

    assert docker.resolve_image_tag() == "latest"


def test_get_versioned_images_expands_the_tag_and_skips_third_party(
    tmp_path, monkeypatch
):
    plan = _preflight_plan(tmp_path, monkeypatch)
    monkeypatch.setenv("TAG", "9.9.9")

    assert docker.get_versioned_images(plan) == [f"{DEPS_IMAGE}:9.9.9"]


def test_get_versioned_images_is_empty_without_built_images(tmp_path, monkeypatch):
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  postgres:
    image: postgres:17.2
    profiles: ["prof1"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    assert docker.get_versioned_images({"compose-test.yml": ["prof1"]}) == []


def _mock_preflight_client(monkeypatch, local: bool) -> MagicMock:
    """Point the preflight at one built image and a fake Docker client."""
    mock_client = MagicMock()
    mock_client.image.exists.return_value = local
    monkeypatch.setattr(docker, "client", mock_client)
    monkeypatch.setattr(
        docker, "get_versioned_images", lambda plan: [f"{DEPS_IMAGE}:9.9.9"]
    )
    return mock_client


def test_find_unpublished_images_accepts_an_image_already_on_the_host(monkeypatch):
    """An offline machine must still start a stack whose images it has pulled."""
    mock_client = _mock_preflight_client(monkeypatch, local=True)

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []
    mock_client.manifest.inspect.assert_not_called()


def test_find_unpublished_images_accepts_a_published_image(monkeypatch):
    mock_client = _mock_preflight_client(monkeypatch, local=False)

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []
    mock_client.manifest.inspect.assert_called_once_with(f"{DEPS_IMAGE}:9.9.9")


def test_find_unpublished_images_reports_an_absent_tag(monkeypatch):
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException("manifest unknown\n")

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == [
        f"{DEPS_IMAGE}:9.9.9"
    ]


def test_find_unpublished_images_passes_an_unreachable_registry(monkeypatch):
    """No network is not evidence that a tag is absent, so the launch goes on."""
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException(
        'Get "https://ghcr.io/v2/": dial tcp: lookup ghcr.io: no such host\n'
    )

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []


def test_a_failure_that_says_not_found_is_not_an_absent_tag(monkeypatch):
    """Only Docker's answer for an absent tag stops a launch. `docker manifest
    inspect` reports one as "no such manifest: <reference>" (docker/cli
    internal/registryclient/fetcher.go), and the registry's own code is
    MANIFEST_UNKNOWN. A missing credential helper fails with "error getting
    credentials - err: exec: ...: executable file not found in $PATH"
    (docker-credential-helpers client/client.go, Go's os/exec ErrNotFound),
    which says nothing about the tag."""
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException(
        'error getting credentials - err: exec: "docker-credential-desktop": '
        "executable file not found in $PATH, out: ``\n"
    )

    assert docker._registry_has_image(f"{DEPS_IMAGE}:9.9.9") is None
    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == []


def test_docker_names_an_absent_tag_no_such_manifest(monkeypatch):
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.manifest.inspect.side_effect = FakeDockerException(
        f"no such manifest: {DEPS_IMAGE}:9.9.9\n"
    )

    assert docker._registry_has_image(f"{DEPS_IMAGE}:9.9.9") is False


def test_find_unpublished_images_survives_a_broken_local_lookup(monkeypatch):
    """A daemon error on the local lookup must not hide the registry answer."""
    mock_client = _mock_preflight_client(monkeypatch, local=False)
    mock_client.image.exists.side_effect = Exception("cannot connect to the daemon")
    mock_client.manifest.inspect.side_effect = FakeDockerException("manifest unknown\n")

    assert docker.find_unpublished_images({"compose-test.yml": ["prof1"]}) == [
        f"{DEPS_IMAGE}:9.9.9"
    ]


def test_running_one_shot_container_is_awaited(monkeypatch):
    """A running seaweed-init is waited for; an exited or missing one is not."""
    mock_client = MagicMock()
    monkeypatch.setattr(docker, "client", mock_client)

    mock_client.container.exists.return_value = True
    mock_client.container.inspect.return_value.state.running = True
    docker.wait_for_one_shot_containers()
    mock_client.container.wait.assert_called_once_with("seaweed-init")

    mock_client.container.wait.reset_mock()
    mock_client.container.inspect.return_value.state.running = False
    docker.wait_for_one_shot_containers()
    mock_client.container.wait.assert_not_called()

    mock_client.container.exists.return_value = False
    docker.wait_for_one_shot_containers()
    mock_client.container.wait.assert_not_called()


def test_get_stack_details_shows_the_tag_that_will_run(tmp_path, monkeypatch):
    """explain printed `${TAG:-latest}` as written, not the tag compose uses."""
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
services:
  db:
    image: ghcr.io/jaehyeon-kim/odctl/postgres:${TAG:-latest}
    profiles: ["postgres"]
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.setenv("TAG", "1.0.1")
    _, _, images, _ = docker.get_stack_details("compose-test.yml", ["postgres"])
    assert images == ["db -> ghcr.io/jaehyeon-kim/odctl/postgres:1.0.1"]


@pytest.mark.parametrize(
    "value, expected",
    [
        ("${SET}-$SET-$$SET", "on-on-$SET"),
        ("${MISSING:-d} ${EMPTY:-d} ${EMPTY-d} ${MISSING-d}", "d d  d"),
        ("${MISSING:?e}|${EMPTY?e}|${SET:?e}", "||on"),
        ("${SET:+r} ${EMPTY:+r} ${EMPTY+r} ${MISSING+r}", "r  r "),
        ("${MISSING:-${SET:-x}-data}", "on-data"),
        ("${1BAD} and ${UNCLOSED", "${1BAD} and ${UNCLOSED"),
    ],
    ids=[
        "plain and escape",
        "defaults",
        "required",
        "replacements",
        "nested",
        "invalid",
    ],
)
def test_expand_follows_compose_interpolation(value, expected):
    """A workspace file may use any form the Compose specification and Docker's docs list."""
    env = {"SET": "on", "EMPTY": ""}

    assert docker.expand(value, env) == expected


def test_get_declared_volumes_gives_the_names_docker_lists(tmp_path, monkeypatch):
    """A service mounts a volume by its key, and Docker lists it by its name."""
    compose_path = tmp_path / "compose-test.yml"
    compose_path.write_text("""
name: odctl-test
volumes:
  events:
    name: ${PREFIX:-odctl}-events
  plain:
    name: plain-data
  default-named: {}
  shared:
    external: true
""")
    monkeypatch.setattr(docker, "get_compose_path", lambda x: compose_path)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.setenv("PREFIX", "team")

    assert docker.get_declared_volumes("compose-test.yml") == {
        "events": "team-events",
        "plain": "plain-data",
        "default-named": "odctl-test_default-named",
        "shared": "shared",
    }


# ==========================================
# The workspace .env, read as Compose reads it
# ==========================================

# Each form Docker documents for `.env` ("Interpolation", .env file syntax), with the
# value Compose gives it. Compose reads the file with compose-go's dotenv parser
# (dotenv/parser.go), which the comments name where a case follows its code.
ENV_FORMS = [
    ("TAG=1.9.0\n", "1.9.0"),
    ("# TAG=0.1.0\n\nTAG=1.9.0\n", "1.9.0"),
    ("TAG=1.9.0 # pinned\n", "1.9.0"),
    # Why: only " #" starts an inline comment (extractVarValue cuts at " #").
    ("TAG=1.9.0#pinned\n", "1.9.0#pinned"),
    ('TAG="1.10.0" # c\n', "1.10.0"),
    ("TAG='1.10.0' # c\n", "1.10.0"),
    ("TAG: 1.9.0\n", "1.9.0"),
    ("TAG =  1.9.0  \n", "1.9.0"),
    ("export TAG=1.9.0\n", "1.9.0"),
    ("TAG=1.9.0\nTAG=1.10.0\n", "1.10.0"),
    ("TAG='a\\nb $X'\n", "a\\nb $X"),
    ("TAG='line one\nline two'\n", "line one\nline two"),
    ('TAG="a\\tb\\nc\\\\d"\n', "a\tb\nc\\d"),
    ('TAG="say \\"hi\\""\n', 'say "hi"'),
    ("TAG='it\\'s'\n", "it's"),
    ("BASE=1.9\nTAG=${BASE}.0\n", "1.9.0"),
    ('BASE=1.9\nTAG="${BASE}.0"\n', "1.9.0"),
    ("TAG=${MISSING:-1.9.0}\n", "1.9.0"),
    # Why: `\$` and `$$` both give a literal `$` (expandEscapes, then interpolation).
    ('TAG="\\$BASE"\n', "$BASE"),
    ("TAG=$$BASE\n", "$BASE"),
]


@pytest.mark.parametrize("text, tag", ENV_FORMS, ids=[t for t, _ in ENV_FORMS])
def test_the_env_file_is_read_as_compose_reads_it(tmp_path, monkeypatch, text, tag):
    (tmp_path / ".env").write_text(text)
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.delenv("TAG", raising=False)
    monkeypatch.delenv("BASE", raising=False)
    monkeypatch.delenv("MISSING", raising=False)

    assert docker.resolve_image_tag() == tag


def test_the_shell_wins_when_the_env_file_interpolates(tmp_path, monkeypatch):
    """compose-go looks a variable up in the environment first, then in the lines
    above it (dotenv/godotenv.go, expandVariables)."""
    (tmp_path / ".env").write_text("BASE=1.9\nTAG=${BASE}.0\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)
    monkeypatch.setenv("BASE", "2.0")

    assert docker.resolve_image_tag() == "2.0.0"


def test_a_line_compose_rejects_does_not_hide_the_others(tmp_path, monkeypatch):
    """compose-go stops at a key with a space or a character outside letters, digits
    and `_.-[]` (locateKeyName), and Compose reports it when it runs. odctl reads
    the file only to show and check TAG, so it skips that line and reads the rest."""
    (tmp_path / ".env").write_text("MY KEY=x\nBAD!=y\nTAG=1.9.0\n")
    monkeypatch.setattr(docker, "get_active_dir", lambda: tmp_path)

    assert docker.resolve_image_tag() == "1.9.0"
