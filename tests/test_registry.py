import pytest
from pydantic import ValidationError

from odctl.registry import Registry, load_registry


def test_registry_pydantic_validation(mock_registry_data):
    """Ensures a populated Pydantic model instantiates flawlessly with correct types."""
    assert isinstance(mock_registry_data.capacities, dict)
    assert "infra" in mock_registry_data.stacks
    assert mock_registry_data.stacks["infra"].file == "compose-infra.yml"


def test_registry_validation_missing_fields():
    """Should catch formatting errors if critical keys are dropped from configuration."""
    bad_data = {
        "stacks": {
            "broken-stack": {
                # missing 'file' and 'profiles'
                "description": "Invalid stack configuration"
            }
        }
    }
    with pytest.raises(ValidationError):
        Registry(**bad_data)


def test_load_registry_file_not_found(mock_workspace, monkeypatch):
    """Should raise standard FileNotFoundError if registry file is missing entirely."""
    monkeypatch.setattr(
        "odctl.config.get_registry_path", lambda: mock_workspace / "ghost_registry.yml"
    )
    with pytest.raises(FileNotFoundError):
        load_registry()


class TestUsageTextMatchesCompose:
    """
    registry.yml usage text is what `odctl explain` prints, so a wrong port is
    wrong advice. Nothing compared it against the compose files, which is how a
    wrong MLflow port shipped once and how the Alertmanager port stayed wrong
    from the day it was written.
    """

    @staticmethod
    def _resources():
        from pathlib import Path

        import odctl.config as config

        return Path(config.__file__).parent / "resources"

    def _load(self):
        import yaml

        root = self._resources()
        registry = yaml.safe_load((root / "registry.yml").read_text())
        composes = {
            p.name: yaml.safe_load(p.read_text()) for p in root.glob("compose-*.yml")
        }
        return root, registry, composes

    @staticmethod
    def _published_ports(compose: dict, profile: str) -> set:
        """Host ports the compose file publishes for services in this profile."""
        ports = set()
        for svc in (compose.get("services") or {}).values():
            if not isinstance(svc, dict) or profile not in (svc.get("profiles") or []):
                continue
            for entry in svc.get("ports") or []:
                if isinstance(entry, str):
                    host = entry.split(":")[0].strip('"')
                elif isinstance(entry, dict):
                    host = str(entry.get("published", ""))
                else:
                    continue
                if host.isdigit():
                    ports.add(int(host))
        return ports

    def test_every_host_port_in_usage_text_is_published(self):
        import re

        _, registry, composes = self._load()
        wrong = []
        for stack in registry["stacks"].values():
            usage = stack.get("usage")
            if not isinstance(usage, dict):
                continue
            compose = composes.get(stack["file"])
            if compose is None:
                continue
            for profile, text in usage.items():
                published = self._published_ports(compose, profile)
                for port in re.findall(r"127\.0\.0\.1:(\d+)", text or ""):
                    if int(port) not in published:
                        wrong.append(f"{profile}: usage says 127.0.0.1:{port}")
        assert not wrong, (
            "usage text names ports the profile does not publish: " + "; ".join(wrong)
        )

    def test_every_internal_hostname_in_usage_text_resolves(self):
        import re

        _, registry, composes = self._load()
        names = set()
        for compose in composes.values():
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

        # Named in the text precisely to say it does not resolve from the host.
        allowed = {"host.minikube.internal"}

        unknown = []
        for stack in registry["stacks"].values():
            usage = stack.get("usage")
            if not isinstance(usage, dict):
                continue
            for profile, text in usage.items():
                for host in re.findall(
                    r"(?:https?://)?([a-z][a-z0-9.-]*):\d+", text or ""
                ):
                    if host == "127.0.0.1" or host in allowed:
                        continue
                    if host not in names:
                        unknown.append(f"{profile}: {host}")
        assert not unknown, (
            "usage text names hosts no container provides: " + "; ".join(unknown)
        )
