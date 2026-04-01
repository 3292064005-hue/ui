from __future__ import annotations

from pathlib import Path

from robot_sim.app.runtime_paths import resolve_runtime_paths


def test_resolve_runtime_paths_uses_packaged_resources_when_source_layout_missing(tmp_path, monkeypatch):
    export_root = tmp_path / 'custom-exports'
    monkeypatch.setenv('ROBOT_SIM_EXPORT_DIR', str(export_root))
    paths = resolve_runtime_paths(tmp_path / 'missing-root')
    assert paths.source_layout_available is False
    assert paths.config_root.name == 'configs'
    assert paths.logging_config_path.name == 'logging.yaml'
    assert paths.plugin_manifest_path.name == 'plugins.yaml'
    assert paths.export_root == export_root
    assert paths.robot_root.name == 'robots'


def test_resolve_runtime_paths_prefers_source_layout(project_root: Path):
    paths = resolve_runtime_paths(project_root)
    assert paths.source_layout_available is True
    assert paths.config_root == project_root / 'configs'
    assert paths.export_root == project_root / 'exports'
