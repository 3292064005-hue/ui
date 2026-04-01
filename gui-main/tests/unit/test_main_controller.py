from __future__ import annotations

import numpy as np
import pytest

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController
from robot_sim.model.ik_result import IKResult


def test_main_controller_trajectory_goal_requires_successful_ik(project_root):
    controller = MainController(project_root, container=build_container(project_root))
    controller.load_robot('planar_2dof')
    with pytest.raises(RuntimeError):
        controller.trajectory_goal_or_raise()

    controller.state_store.patch(
        ik_result=IKResult(
            success=True,
            q_sol=np.array([0.3, -0.2]),
            logs=tuple(),
            message='converged',
            final_pos_err=0.0,
            final_ori_err=0.0,
            stop_reason='converged',
        )
    )
    goal = controller.trajectory_goal_or_raise()
    assert np.allclose(goal, [0.3, -0.2])
