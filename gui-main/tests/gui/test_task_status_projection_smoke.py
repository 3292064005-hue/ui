from __future__ import annotations

import pytest

pytest.importorskip('PySide6')

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.main_window import MainWindow


def test_task_snapshot_reaches_state_store():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    root = get_project_root()
    w = MainWindow(root, container=build_container(root))
    snap = TaskSnapshot(task_id='t1', task_kind='ik', task_state=TaskState.RUNNING)
    w._on_task_state_changed(snap)
    assert w.controller.state.active_task_snapshot is snap
    w.close()
