from __future__ import annotations

import sys
import types
from pathlib import Path

from robot_sim.app import bootstrap as bootstrap_mod
from robot_sim.app import main as main_mod


def test_bootstrap_uses_runtime_paths_and_dependencies(monkeypatch):
    root = Path('/tmp/fake-project')
    called: dict[str, object] = {}

    class DummyPaths:
        def __init__(self, root_path):
            self.project_root = root_path
            self.logging_config_path = root_path / 'runtime' / 'logging.yaml'
            self.config_root = root_path / 'runtime'
            self.export_root = root_path / 'exports'
            self.resource_root = root_path
            self.source_layout_available = False

    monkeypatch.setattr(bootstrap_mod, 'get_project_root', lambda: root)
    monkeypatch.setattr(bootstrap_mod, 'resolve_runtime_paths', lambda: DummyPaths(root))
    monkeypatch.setattr(bootstrap_mod, 'setup_logging', lambda path: called.setdefault('logging_path', path))

    def fake_build_container(value):
        called['container_root'] = value
        return 'container'

    monkeypatch.setattr(bootstrap_mod, 'build_container', fake_build_container)

    result_root, container = bootstrap_mod.bootstrap()

    assert result_root == root
    assert container == 'container'
    assert called['logging_path'] == root / 'runtime' / 'logging.yaml'
    assert getattr(called['container_root'], 'project_root') == root


def test_main_returns_1_when_pyside_missing(monkeypatch, capsys):
    monkeypatch.setattr(main_mod, 'bootstrap', lambda: (Path('/tmp/fake-project'), object()))
    monkeypatch.delitem(sys.modules, 'PySide6', raising=False)
    monkeypatch.delitem(sys.modules, 'PySide6.QtWidgets', raising=False)

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'PySide6.QtWidgets':
            raise ModuleNotFoundError('PySide6 missing')
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr('builtins.__import__', fake_import)
    assert main_mod.main() == 1
    captured = capsys.readouterr()
    assert 'PySide6 未安装' in captured.out


def test_main_launches_window_when_qt_is_available(monkeypatch):
    events: list[object] = []

    class FakeApp:
        def __init__(self, argv):
            events.append(('argv', list(argv)))

        def exec(self):
            events.append('exec')
            return 7

    class FakeWindow:
        def __init__(self, root, *, container):
            events.append(('window_root', root))
            events.append(('window_container', container))

        def show(self):
            events.append('show')

    qtwidgets = types.ModuleType('PySide6.QtWidgets')
    qtwidgets.QApplication = FakeApp
    monkeypatch.setitem(sys.modules, 'PySide6', types.ModuleType('PySide6'))
    monkeypatch.setitem(sys.modules, 'PySide6.QtWidgets', qtwidgets)

    fake_window_mod = types.ModuleType('robot_sim.presentation.main_window')
    fake_window_mod.MainWindow = FakeWindow
    monkeypatch.setitem(sys.modules, 'robot_sim.presentation.main_window', fake_window_mod)
    fake_container = object()
    monkeypatch.setattr(main_mod, 'bootstrap', lambda: (Path('/tmp/fake-project'), fake_container))

    assert main_mod.main() == 7
    assert ('window_root', Path('/tmp/fake-project')) in events
    assert ('window_container', fake_container) in events
    assert 'show' in events
    assert 'exec' in events
