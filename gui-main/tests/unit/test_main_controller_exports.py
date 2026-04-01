from __future__ import annotations

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def test_main_controller_exports_trajectory_metrics(project_root):
    controller = MainController(project_root, container=build_container(project_root))
    controller.load_robot('planar_2dof')
    controller.state_store.patch(
        ik_result=type('Obj', (), {'success': True, 'q_sol': controller.state.q_current.copy()})()
    )
    traj = controller.plan_trajectory(q_goal=controller.state.q_current, duration=1.0, dt=0.1)
    path = controller.export_trajectory_metrics('metrics_test.json', {'num_samples': int(traj.t.shape[0])})
    assert path.exists()
