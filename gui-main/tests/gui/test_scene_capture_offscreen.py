from __future__ import annotations

import pytest

pytest.importorskip('PySide6')

from robot_sim.render.scene_3d_widget import Scene3DWidget


def test_scene_widget_snapshot_available_without_plotter():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    widget = Scene3DWidget()
    snap = widget.scene_snapshot()
    assert 'overlay_text' in snap
