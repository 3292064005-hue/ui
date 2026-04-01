from __future__ import annotations

import pytest

pytest.importorskip('PySide6')

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.presentation.main_window import MainWindow


def test_main_window_has_core_bindable_widgets():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    root = get_project_root()
    w = MainWindow(root, container=build_container(root))
    assert w.scene_toolbar is not None
    assert w.playback_panel is not None
    assert w.solver_panel is not None
    assert w.status_panel is not None
    w.close()
