import sys
from pathlib import Path

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


def test_plugin_loader_resolves_whitelisted_factory(tmp_path: Path, monkeypatch):
    plugin_module = tmp_path / 'demo_plugin.py'
    plugin_module.write_text(
        'class DemoSolver:\n'
        '    pass\n\n'
        'def build_plugin():\n'
        '    return {\"instance\": DemoSolver(), \"metadata\": {\"family\": \"iterative\"}, \"aliases\": (\"demo_alias\",)}\n',
        encoding='utf-8',
    )
    manifest = tmp_path / 'plugins.yaml'
    manifest.write_text(
        'plugins:\n'
        '  - id: demo_solver\n'
        '    kind: solver\n'
        '    factory: demo_plugin:build_plugin\n'
        '    enabled_profiles: [research]\n',
        encoding='utf-8',
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.path.insert(0, str(tmp_path))
    try:
        loader = PluginLoader(manifest, policy=RuntimeFeaturePolicy(active_profile='research', plugin_discovery_enabled=True))
        registrations = loader.registrations('solver')
        assert len(registrations) == 1
        registration = registrations[0]
        assert registration.plugin_id == 'demo_solver'
        assert registration.aliases == ('demo_alias',)
        assert registration.metadata['family'] == 'iterative'
    finally:
        while str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
