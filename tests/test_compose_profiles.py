"""Static checks on profile wiring in the packaged compose files.

These exist because of a real failure. `odctl down --all --volumes` selected the
`catalog` profile on its own, since teardown picks profiles by running state and
by volume ownership. That service declares a `depends_on` on services gated
behind the `postgres` and `storage` profiles, so compose rejected the file with
"depends on undefined service" before contacting Docker, and teardown aborted for
every profile group.

Nothing here needs Docker, so it belongs in the unit suite rather than in the
end-to-end tests, which run only on tags and so cannot fail a pull request.
"""

from unittest import mock

import pytest
import yaml
from typer.testing import CliRunner

from odctl import config
from odctl.main import app
from odctl.config import get_internal_resources_dir
from odctl.planner import (
    build_execution_plan,
    expand_plan_dependencies,
    expand_same_file_dependencies,
)
from odctl.registry import load_registry

runner = CliRunner()


@pytest.fixture(autouse=True)
def _read_packaged_resources(monkeypatch):
    """Read the registry from the packaged resources, not a local workspace.

    Without this the compose files come from src/odctl/resources while the
    registry comes from ./.odctl, so an inconsistency between the two is
    invisible to these tests.
    """
    monkeypatch.setattr(config, "get_active_dir", get_internal_resources_dir)


def _compose_files():
    return sorted(get_internal_resources_dir().glob("compose-*.yml"))


def _services(path):
    return (yaml.safe_load(path.read_text()) or {}).get("services") or {}


def _depends_on(service):
    dep = service.get("depends_on")
    if isinstance(dep, dict):
        return list(dep.keys())
    return list(dep or [])


def _profiles_of_file(path):
    seen = []
    for svc in _services(path).values():
        for profile in svc.get("profiles") or []:
            if profile not in seen:
                seen.append(profile)
    return seen


def test_every_teardown_selection_yields_a_valid_project():
    """Selecting any single profile, then widening it the way teardown does,
    must leave every depends_on target inside the active set.

    This is the property that actually matters: teardown may select one profile
    of a file, so after expansion the resulting project has to be well-formed.
    """
    violations = []
    for path in _compose_files():
        services = _services(path)
        for profile in _profiles_of_file(path):
            active = set(
                expand_same_file_dependencies(_profiles_of_file(path), [profile])
            )
            live = {
                name
                for name, svc in services.items()
                if not svc.get("profiles") or (set(svc["profiles"]) & active)
            }
            for name in sorted(live):
                for target in _depends_on(services[name]):
                    if target not in live:
                        violations.append(
                            f"{path.name}: selecting {profile} activates {name}, "
                            f"which depends on {target}, absent from the project"
                        )
    assert not violations, (
        "a teardown selection would produce an invalid compose project:\n"
        + "\n".join(violations)
    )


def test_expansion_pulls_in_same_file_dependencies():
    """Selecting `catalog` must widen to `postgres` and `storage`.

    This is the concrete case that broke: `catalog` owns no volume of its own but
    mounts the shared dependency volume, so `--volumes` selects it even when
    nothing of it is running.
    """
    expanded = expand_same_file_dependencies(
        ["postgres", "storage", "catalog"], ["catalog"]
    )
    assert expanded == ["postgres", "storage", "catalog"]


def test_expansion_stays_within_the_file():
    """Dependencies declared outside the file must not be added.

    Each file is torn down by its own compose call, so widening across files
    would stop shared infrastructure other profiles may still be using.
    """
    registry = load_registry()
    catalog_deps = None
    for stack in registry.stacks.values():
        if "catalog" in (stack.depends_on or {}):
            catalog_deps = stack.depends_on["catalog"]
    assert catalog_deps and "deps" in catalog_deps, "expected catalog to depend on deps"

    expanded = expand_same_file_dependencies(
        ["postgres", "storage", "catalog"], ["catalog"]
    )
    assert "deps" not in expanded


def test_expansion_is_a_noop_without_dependencies():
    """A profile with no same-file dependencies is returned unchanged."""
    assert expand_same_file_dependencies(
        ["kafka-lite", "kafka-full"], ["kafka-lite"]
    ) == ["kafka-lite"]


def test_named_profile_plan_is_widened():
    """Naming profiles directly must widen the same way `--all` does.

    This is the regression the tests above could not catch. They exercise the
    helper, while the bug was that `down` only called it inside its `--all`
    branch, so `odctl down storage catalog trino` handed compose a project where
    catalog depended on a postgres the profile filter had removed, and every
    teardown of a named selection aborted.
    """
    plan = build_execution_plan(
        ["storage", "catalog", "trino"], False, resolve_deps=False
    )
    assert plan["compose-infra.yml"] == ["storage", "catalog"], (
        "precondition changed: the raw plan is expected to omit postgres"
    )

    widened = expand_plan_dependencies(plan)
    assert widened["compose-infra.yml"] == ["postgres", "storage", "catalog"]


def test_plan_widening_does_not_cross_files():
    """Widening one file must not add profiles to another.

    Each file gets its own compose call, so pulling a dependency across files
    would stop infrastructure that other profiles are still using.
    """
    plan = build_execution_plan(["catalog", "trino"], False, resolve_deps=False)
    widened = expand_plan_dependencies(plan)

    assert widened["compose-analytics.yml"] == plan["compose-analytics.yml"]
    assert "postgres" not in widened["compose-analytics.yml"]


def test_plan_widening_is_idempotent():
    """Widening an already-valid plan must change nothing.

    `down --all` filters by running state and then widens, so the same plan can
    pass through expansion twice. That has to be safe.
    """
    plan = build_execution_plan(["catalog"], False, resolve_deps=False)
    once = expand_plan_dependencies(plan)
    assert expand_plan_dependencies(once) == once


def test_down_widens_a_named_profile():
    """`odctl down catalog` must plan to stop postgres as well.

    This is the only test here that exercises the command rather than the
    planner, and it is the one that fails without the fix. Every other test in
    this file passes while `down` is broken, because they call the helper
    directly and the bug was that `down` reached it only on its `--all` branch.
    `--dry-run` returns before the Docker check, so this needs no daemon.
    """
    result = runner.invoke(app, ["down", "catalog", "--dry-run"])

    assert result.exit_code == 0, result.stdout
    assert "compose-infra.yml" in result.stdout
    assert "postgres" in result.stdout, (
        "catalog depends on postgres, so a teardown that omits it hands compose "
        "an invalid project:\n" + result.stdout
    )


def test_restart_widens_a_named_profile():
    """`odctl restart catalog` must resolve the same widened plan.

    `down`, `ps`, `logs` and `restart` all build their plan with
    `resolve_deps=False` and all pass profiles to a compose client, so all four
    need the widening. This pins the one with no dry-run of its own.
    """
    captured = {}
    with (
        mock.patch("odctl.main.is_docker_running", return_value=True),
        mock.patch(
            "odctl.main.restart_managed_containers",
            side_effect=lambda plan: captured.update(plan),
        ),
    ):
        result = runner.invoke(app, ["restart", "catalog"])

    assert result.exit_code == 0, result.stdout
    assert "postgres" in captured.get("compose-infra.yml", []), (
        f"expected postgres in the restart plan, got {captured}"
    )


def test_recreate_widens_a_named_profile():
    """`odctl recreate catalog` needs the same widening as restart.

    It builds its plan with `resolve_deps=False` and hands the profiles to a
    compose client, so without the widening compose gets a project missing the
    dependency that catalog attaches to.
    """
    captured = {}
    with (
        mock.patch("odctl.main.is_docker_running", return_value=True),
        mock.patch(
            "odctl.main.recreate_managed_containers",
            side_effect=lambda plan, pull=False: captured.update(plan),
        ),
    ):
        result = runner.invoke(app, ["recreate", "catalog"])

    assert result.exit_code == 0, result.stdout
    assert "postgres" in captured.get("compose-infra.yml", []), (
        f"expected postgres in the recreate plan, got {captured}"
    )


def test_every_named_selection_yields_a_valid_project():
    """Every single-profile plan must survive widening as a valid project.

    Same property as the teardown test above, asserted one level up through the
    plan so it covers the code path the commands actually take rather than the
    helper in isolation.
    """
    violations = []
    for path in _compose_files():
        services = _services(path)
        for profile in _profiles_of_file(path):
            plan = build_execution_plan([profile], False, resolve_deps=False)
            active = set(expand_plan_dependencies(plan).get(path.name, []))
            live = {
                name
                for name, svc in services.items()
                if not svc.get("profiles") or (set(svc["profiles"]) & active)
            }
            for name in sorted(live):
                for target in _depends_on(services[name]):
                    if target not in live:
                        violations.append(
                            f"{path.name}: naming {profile} activates {name}, "
                            f"which depends on {target}, absent from the project"
                        )
    assert not violations, (
        "a named selection would produce an invalid compose project:\n"
        + "\n".join(violations)
    )


def test_valkey_user_can_use_pubsub_channels():
    """Channels are a separate ACL class from keys, and Valkey defaults to
    resetchannels. Without an explicit channel grant, PUBLISH and SUBSCRIBE return
    NOPERM while every key operation still works, so the account looks healthy and
    only Pub/Sub clients fail. Verified against the image: with `~* +@all` alone,
    ACL LIST reports resetchannels and PUBLISH returns
    "NOPERM No permissions to access a channel".
    """
    compose = yaml.safe_load(
        (get_internal_resources_dir() / "compose-store.yml").read_text()
    )
    command = compose["services"]["valkey"]["command"]

    assert "~*" in command, "the valkey user should have access to all keys"
    assert "&*" in command, (
        "the valkey user needs an explicit channel grant, because +@all grants "
        "commands and ~* grants keys, and neither grants channels"
    )


class TestConfigHostnamesResolve:
    """
    A config that names a host no container provides fails at runtime, silently
    and long after startup. Three faults of exactly this shape were found in
    September 2026: prometheus scraped clickhouse-11 to clickhouse-22 where the
    containers are ch-11 to ch-22, fluss pointed at clickhouse-keeper where the
    service is ch-keeper, and a Trino catalog once named clickhouse-11, which
    was the 0.2.0 regression. None needs a container to catch.
    """

    # Any scheme, not just http, because a Trino catalog names its host inside a
    # JDBC URL: jdbc:clickhouse://ch-11:8123. That is the shape of the 0.2.0
    # regression, so missing it would defeat the purpose.
    #
    # A port is two to five digits not followed by another digit, a dot or a
    # dash, so an image tag like flink:2.1-java17 is not read as a host.
    HOST_PORT = r"(?:://|@|[\s=\"']|^)([a-z][a-z0-9.-]*):\d{2,5}(?![\d.\-])"

    @staticmethod
    def _resources():
        from pathlib import Path

        import odctl.config as config

        return Path(config.__file__).parent / "resources"

    @classmethod
    def _valid_hosts(cls) -> set:
        """Service names, container names and network aliases across all files."""
        import yaml

        names = set()
        for path in cls._resources().glob("compose-*.yml"):
            compose = yaml.safe_load(path.read_text()) or {}
            for svc_name, svc in (compose.get("services") or {}).items():
                names.add(svc_name)
                if not isinstance(svc, dict):
                    continue
                if svc.get("container_name"):
                    names.add(svc["container_name"])
                networks = svc.get("networks")
                if isinstance(networks, dict):
                    for net in networks.values():
                        if isinstance(net, dict):
                            names.update(net.get("aliases") or [])
        return names

    @classmethod
    def _mounted_configs(cls) -> list:
        """Files a compose service bind-mounts from the resources directory."""
        import yaml

        root = cls._resources()
        found = []
        for path in root.glob("compose-*.yml"):
            compose = yaml.safe_load(path.read_text()) or {}
            for svc in (compose.get("services") or {}).values():
                if not isinstance(svc, dict):
                    continue
                for volume in svc.get("volumes") or []:
                    if not isinstance(volume, str) or not volume.startswith("./"):
                        continue
                    target = root / volume.split(":")[0][2:]
                    if target.is_file():
                        found.append(target)
                    elif target.is_dir():
                        found.extend(p for p in target.rglob("*") if p.is_file())
        return sorted(set(found))

    def test_every_host_port_in_a_mounted_config_resolves(self):
        import re

        root = self._resources()
        valid = self._valid_hosts()
        # Addresses that are deliberately not a container on the odctl network.
        allowed = {
            "localhost",
            "0.0.0.0",
            "127.0.0.1",
            "host.minikube.internal",
            "host.docker.internal",
        }

        unknown = []
        for path in self._mounted_configs():
            try:
                text = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for host in set(re.findall(self.HOST_PORT, text, re.M)):
                if host in allowed or host in valid or "." in host:
                    continue
                unknown.append(f"{path.relative_to(root)} names {host}")
        assert not unknown, "config names hosts no container provides: " + "; ".join(
            sorted(unknown)
        )

    def test_every_host_in_a_compose_environment_resolves(self):
        import re

        import yaml

        root = self._resources()
        valid = self._valid_hosts()
        allowed = {"localhost", "0.0.0.0", "127.0.0.1", "host.minikube.internal"}

        unknown = []
        for path in root.glob("compose-*.yml"):
            compose = yaml.safe_load(path.read_text()) or {}
            for svc_name, svc in (compose.get("services") or {}).items():
                if not isinstance(svc, dict):
                    continue
                blob = yaml.dump(
                    {
                        k: v
                        for k, v in svc.items()
                        if k in ("environment", "command", "healthcheck")
                    }
                )
                for host in set(re.findall(self.HOST_PORT, blob, re.M)):
                    if host in allowed or host in valid or "." in host:
                        continue
                    unknown.append(f"{path.name}:{svc_name} names {host}")
        assert not unknown, "compose names hosts no container provides: " + "; ".join(
            sorted(unknown)
        )

    def test_every_host_style_env_var_resolves(self):
        """
        Many services name a peer without a port, as DB_HOST or
        ELASTICSEARCH_HOST, so the host:port pattern cannot see them. A typo
        there fails exactly like a wrong scrape target, and just as quietly.
        """
        import re

        import yaml

        valid = self._valid_hosts()
        # Bind addresses and values that are not a peer at all.
        allowed = {"0.0.0.0", "::", "localhost", "127.0.0.1", "host.minikube.internal"}
        keys = re.compile(r"(_HOST|_HOSTNAME|_ADDR|_ADDRESS|_SERVER|_NODES?)$")

        unknown = []
        for path in self._resources().glob("compose-*.yml"):
            compose = yaml.safe_load(path.read_text()) or {}
            for svc_name, svc in (compose.get("services") or {}).items():
                if not isinstance(svc, dict):
                    continue
                env = svc.get("environment")
                if not isinstance(env, dict):
                    continue
                for key, value in env.items():
                    if not isinstance(value, str) or not keys.search(key):
                        continue
                    # Skip anything with a port, a variable, or a scheme: the
                    # other two tests cover those.
                    if ":" in value or "$" in value or "/" in value or not value:
                        continue
                    if value in allowed or value in valid or "." in value:
                        continue
                    unknown.append(f"{path.name}:{svc_name} {key}={value}")
        assert not unknown, "env var names a host no container provides: " + "; ".join(
            sorted(unknown)
        )


class TestComposeShape:
    """
    Two mistakes that compose accepts silently. Both were found by hand in
    September 2026 and neither is visible without looking for it.
    """

    @staticmethod
    def _compose_files():
        from pathlib import Path

        import odctl.config as config

        return sorted(
            (Path(config.__file__).parent / "resources").glob("compose-*.yml")
        )

    def test_mem_limit_is_never_nested_where_compose_ignores_it(self):
        """
        mem_limit is a service-level key. Nested under environment it parses,
        applies nothing, and the container runs uncapped. compose-metadata.yml
        shipped that way and openmetadata-ingestion had no limit at all.
        """
        import yaml

        misplaced = []
        for path in self._compose_files():
            services = (yaml.safe_load(path.read_text()) or {}).get("services") or {}

            def walk(node, trail):
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key == "mem_limit" and len(trail) > 1:
                            misplaced.append(f"{path.name}: {'.'.join(trail)}.{key}")
                        walk(value, trail + [str(key)])
                elif isinstance(node, list):
                    for index, value in enumerate(node):
                        walk(value, trail + [str(index)])

            walk(services, [])
        assert not misplaced, "mem_limit nested where compose ignores it: " + "; ".join(
            misplaced
        )

    def test_no_image_uses_a_floating_tag(self):
        """
        A floating tag changes the stack with no commit and no dashboard entry,
        so a break has no diff to blame. ch-shard2-stub shipped on alpine:latest.
        """
        import yaml

        floating = []
        for path in self._compose_files():
            services = (yaml.safe_load(path.read_text()) or {}).get("services") or {}
            for name, svc in services.items():
                if not isinstance(svc, dict):
                    continue
                image = svc.get("image")
                if not isinstance(image, str) or "${" in image:
                    continue
                tag = image.split("/")[-1]
                if image.endswith(":latest") or ":" not in tag:
                    floating.append(f"{path.name}:{name} -> {image}")
        assert not floating, "image uses a floating tag: " + "; ".join(floating)

    def test_every_env_var_the_cli_writes_is_read_by_a_compose_file(self):
        """
        init_workspace writes variables into .odctl/.env for users to set.
        compose-orch.yml read _PIP_ADDITIONAL_REQUIREMENTS while the CLI wrote
        _AIRFLOW_PIP_DEPS, so setting Airflow extra packages installed nothing
        and nothing said so.
        """
        import re
        from pathlib import Path

        import odctl.workspace as workspace

        source = Path(workspace.__file__).read_text()
        written = set(re.findall(r"""f\.write\(.?['"](_?[A-Z][A-Z0-9_]*)=""", source))
        written |= set(re.findall(r"# (_[A-Z][A-Z0-9_]*)=", source))
        written -= {"TZ"}  # read by service images directly, not by compose.

        referenced = set()
        for path in self._compose_files():
            referenced.update(
                re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", path.read_text())
            )

        orphans = sorted(written - referenced)
        assert not orphans, (
            "the CLI writes these into .env and no compose file reads them: "
            + ", ".join(orphans)
        )
