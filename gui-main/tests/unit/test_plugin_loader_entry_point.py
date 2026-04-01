from __future__ import annotations

from types import SimpleNamespace

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


class _EntryPointsView:
    def __init__(self, items):
        self._items = tuple(items)

    def select(self, *, group: str, name: str):
        return [item for item in self._items if item.group == group and item.name == name]


class _FakeEntryPoint:
    def __init__(self, *, group: str, name: str, payload):
        self.group = group
        self.name = name
        self._payload = payload

    def load(self):
        return self._payload


def test_plugin_loader_supports_entry_point_allowlist(tmp_path, monkeypatch):
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: demo_solver\n'
        '    kind: solver\n'
        '    entry_point: robot_sim.plugins:demo_solver\n'
        '    enabled_profiles: [research]\n',
        encoding='utf-8',
    )

    def payload():
        return {'instance': SimpleNamespace(name='solver'), 'metadata': {'family': 'entry-point'}}
    monkeypatch.setattr(
        'robot_sim.app.plugin_loader.entry_points',
        lambda: _EntryPointsView((_FakeEntryPoint(group='robot_sim.plugins', name='demo_solver', payload=payload),)),
    )

    loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
    registrations = loader.registrations('solver')

    assert len(registrations) == 1
    assert registrations[0].plugin_id == 'demo_solver'
    assert registrations[0].metadata['family'] == 'entry-point'
    assert registrations[0].source == 'entry_point'
