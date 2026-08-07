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
