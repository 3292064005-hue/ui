from __future__ import annotations

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def test_capability_descriptors_include_metadata(project_root):
    controller = MainController(project_root, container=build_container(project_root))
    caps = {cap.key: cap for cap in controller.capabilities()}
    solver_desc = {entry['id']: entry for entry in caps['ik_solvers'].metadata['descriptors']}
    planner_desc = {entry['id']: entry for entry in caps['trajectory_planners'].metadata['descriptors']}
    importer_desc = {entry['id']: entry for entry in caps['robot_importers'].metadata['descriptors']}

    assert 'analytic_6r' in solver_desc
    assert solver_desc['analytic_6r']['metadata']['family'] == 'analytic'
    assert solver_desc['analytic_6r']['aliases'] == ['spherical_wrist_6r']
    assert 'joint_quintic' in planner_desc
    assert planner_desc['waypoint_graph']['metadata']['requires_ik'] is True
    assert 'urdf_skeleton' in importer_desc
    assert importer_desc['urdf_skeleton']['aliases'] == ['urdf']
