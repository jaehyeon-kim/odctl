import pytest
import typer

from odctl.registry import Registry, StackConfig
from odctl.planner import (
    build_execution_plan,
    get_profile_map,
    resolve_dependencies,
    validate_profiles,
)


def test_get_profile_map(mock_workspace, mock_registry_data, monkeypatch):
    """Validates generation of the profile reverse lookup table."""
    monkeypatch.setattr("odctl.planner.load_registry", lambda: mock_registry_data)

    profile_map = get_profile_map()

    assert "storage" in profile_map
    assert profile_map["storage"]["stack_id"] == "infra"
    assert profile_map["storage"]["file"] == "compose-infra.yml"
    assert "spark-master" in profile_map


def test_validate_profiles_success():
    """Should complete silently when checking completely valid profiles."""
    profile_map = {"kafka": {"stack_id": "infra"}}
    # Should not raise any errors
    validate_profiles(["kafka"], profile_map)


def test_validate_profiles_failure():
    """Should trigger an exit sequence when an unknown profile is requested."""
    profile_map = {"kafka": {"stack_id": "infra"}}
    with pytest.raises(typer.Exit) as exc_info:
        validate_profiles(["invalid_profile"], profile_map)
    assert exc_info.value.exit_code == 1


def test_resolve_dependencies(mock_registry_data):
    """Ensures dependency trees are successfully parsed and included."""
    profile_map = {
        "storage": {"stack_id": "infra"},
        "spark-master": {"stack_id": "spark"},
    }

    # Requesting spark-master should automatically pull in storage because of depends_on
    resolved = resolve_dependencies(["spark-master"], profile_map, mock_registry_data)

    assert "spark-master" in resolved
    assert "storage" in resolved


def test_build_execution_plan(mock_workspace, mock_registry_data, monkeypatch):
    """Ensures the execution plan isolates targets into their respective compose files."""
    monkeypatch.setattr("odctl.planner.load_registry", lambda: mock_registry_data)

    plan = build_execution_plan(profiles=["spark-master"])

    # Plan should resolve compose-infra.yml because it's a structural parent dependency
    assert "compose-infra.yml" in plan
    assert "compose-spark.yml" in plan
    assert "storage" in plan["compose-infra.yml"]
    assert "spark-master" in plan["compose-spark.yml"]


class TestUnreachableProfiles:
    """
    A profile resolves to exactly one compose file, the one the registry names.
    A service in another file that declares the same profile is never started,
    and nothing else reports it. ch-keeper declared the fluss profile while
    living in compose-analytics.yml, so fluss ran with no ZooKeeper.
    """

    @staticmethod
    def _setup(tmp_path, monkeypatch, files):
        for name, body in files.items():
            (tmp_path / name).write_text(body)
        monkeypatch.setattr(
            "odctl.docker.get_compose_path", lambda name: tmp_path / name
        )

    def test_reports_a_profile_declared_in_another_file(self, tmp_path, monkeypatch):
        from odctl.planner import find_unreachable_profiles

        registry = Registry(
            stacks={
                "store": StackConfig(
                    file="compose-store.yml", description="d", profiles=["fluss"]
                ),
                "analytics": StackConfig(
                    file="compose-analytics.yml", description="d", profiles=["ch-lite"]
                ),
            },
        )
        monkeypatch.setattr("odctl.planner.load_registry", lambda: registry)
        self._setup(
            tmp_path,
            monkeypatch,
            {
                "compose-store.yml": "services:\n  fluss-coordinator:\n    profiles: ['fluss']\n",
                "compose-analytics.yml": "services:\n  ch-keeper:\n    profiles: ['ch-lite', 'fluss']\n",
            },
        )

        assert find_unreachable_profiles() == [
            ("compose-analytics.yml", "ch-keeper", "fluss")
        ]

    def test_silent_when_every_declaration_matches(self, tmp_path, monkeypatch):
        from odctl.planner import find_unreachable_profiles

        registry = Registry(
            stacks={
                "store": StackConfig(
                    file="compose-store.yml", description="d", profiles=["fluss"]
                ),
                "analytics": StackConfig(
                    file="compose-analytics.yml", description="d", profiles=["ch-lite"]
                ),
            },
        )
        monkeypatch.setattr("odctl.planner.load_registry", lambda: registry)
        self._setup(
            tmp_path,
            monkeypatch,
            {
                "compose-store.yml": "services:\n  fluss-coordinator:\n    profiles: ['fluss']\n",
                "compose-analytics.yml": "services:\n  ch-keeper:\n    profiles: ['ch-lite']\n",
            },
        )

        assert find_unreachable_profiles() == []

    def test_ignores_a_profile_no_stack_declares(self, tmp_path, monkeypatch):
        """An unknown profile is validate_profiles' job, not this check's."""
        from odctl.planner import find_unreachable_profiles

        registry = Registry(
            stacks={
                "store": StackConfig(
                    file="compose-store.yml", description="d", profiles=["fluss"]
                )
            },
        )
        monkeypatch.setattr("odctl.planner.load_registry", lambda: registry)
        self._setup(
            tmp_path,
            monkeypatch,
            {
                "compose-store.yml": "services:\n  x:\n    profiles: ['not-in-registry']\n"
            },
        )

        assert find_unreachable_profiles() == []

    def test_survives_a_missing_or_unparseable_file(self, tmp_path, monkeypatch):
        """A file that is missing, not valid YAML, or whose top level or services
        are a list is left to the command that reads it; a list raised
        AttributeError here, from every `odctl up`."""
        from odctl.planner import find_unreachable_profiles

        registry = Registry(
            stacks={
                "gone": StackConfig(
                    file="compose-gone.yml", description="d", profiles=["a"]
                ),
                "bad": StackConfig(
                    file="compose-bad.yml", description="d", profiles=["b"]
                ),
                "list": StackConfig(
                    file="compose-list.yml", description="d", profiles=["c"]
                ),
                "services": StackConfig(
                    file="compose-services.yml", description="d", profiles=["d"]
                ),
            },
        )
        monkeypatch.setattr("odctl.planner.load_registry", lambda: registry)
        self._setup(
            tmp_path,
            monkeypatch,
            {
                "compose-bad.yml": "services: [oops\n",
                "compose-list.yml": "- a\n",
                "compose-services.yml": "services:\n  - a\n",
            },
        )

        assert find_unreachable_profiles() == []

    def test_warning_names_the_file_service_and_profile(
        self, tmp_path, monkeypatch, capsys
    ):
        from odctl.planner import warn_unreachable_profiles

        monkeypatch.setattr(
            "odctl.planner.find_unreachable_profiles",
            lambda: [("compose-analytics.yml", "ch-keeper", "fluss")],
        )
        warn_unreachable_profiles()

        out = capsys.readouterr().out
        assert "compose-analytics.yml" in out
        assert "ch-keeper" in out
        assert "fluss" in out


def _starts_each_file_after_its_dependencies(plan, profile_map, registry):
    """List each (profile, dependency) whose dependency's file starts later."""
    files = list(plan)
    late = []
    for file, profiles in plan.items():
        for profile in profiles:
            stack = registry.stacks[profile_map[profile]["stack_id"]]
            for dependency in stack.depends_on.get(profile, []):
                if files.index(profile_map[dependency]["file"]) > files.index(file):
                    late.append((profile, dependency))
    return late


def test_every_packaged_request_starts_dependencies_first():
    """Every packaged request of one or two profiles starts the file of each
    dependency before the file that needs it (hunt4's order_check.py)."""
    import itertools

    from odctl.registry import load_registry

    registry = load_registry()
    profile_map = get_profile_map()
    late = []
    for count in (1, 2):
        for request in itertools.combinations(sorted(profile_map), count):
            plan = build_execution_plan(list(request))
            late += _starts_each_file_after_its_dependencies(
                plan, profile_map, registry
            )
    assert late == []


def test_a_dependency_in_another_file_starts_first(tmp_path):
    """`api` sorts before `zookeeper` and has no weight, so the weight table alone
    started the file of `api` first."""
    from odctl import config

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "registry.yml").write_text(
        "stacks:\n"
        "  app:\n    file: compose-app.yml\n    description: d\n    profiles: [api]\n"
        "    depends_on:\n      api: [zookeeper]\n"
        "  zk:\n    file: compose-zk.yml\n    description: d\n    profiles: [zookeeper]\n"
    )
    config.set_workspace_override(workspace)
    try:
        plan = build_execution_plan(["api"])
    finally:
        config.set_workspace_override(None)

    assert list(plan.items()) == [
        ("compose-zk.yml", ["zookeeper"]),
        ("compose-app.yml", ["api"]),
    ]
