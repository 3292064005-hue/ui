from __future__ import annotations

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def test_main_controller_capabilities(project_root):
    controller = MainController(project_root, container=build_container(project_root))
    caps = {cap.key: cap for cap in controller.capabilities()}
    assert 'ik_solvers' in caps
    assert 'trajectory_planners' in caps
    assert 'robot_importers' in caps
    assert 'package_export' in caps
    assert 'dls' in caps['ik_solvers'].metadata['ids']
