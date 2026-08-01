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

import pytest
import yaml

from odctl import config
from odctl.config import get_internal_resources_dir
from odctl.planner import expand_same_file_dependencies
from odctl.registry import load_registry


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
