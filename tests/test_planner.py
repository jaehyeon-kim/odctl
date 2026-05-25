import pytest
import typer

from dml.planner import (
    build_execution_plan,
    get_profile_map,
    resolve_dependencies,
    validate_profiles,
)


def test_get_profile_map(mock_workspace, mock_registry_data, monkeypatch):
    """Validates generation of the profile reverse lookup table."""
    monkeypatch.setattr("dml.planner.load_registry", lambda: mock_registry_data)

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
    monkeypatch.setattr("dml.planner.load_registry", lambda: mock_registry_data)

    plan = build_execution_plan(profiles=["spark-master"])

    # Plan should resolve compose-infra.yml because it's a structural parent dependency
    assert "compose-infra.yml" in plan
    assert "compose-spark.yml" in plan
    assert "storage" in plan["compose-infra.yml"]
    assert "spark-master" in plan["compose-spark.yml"]
