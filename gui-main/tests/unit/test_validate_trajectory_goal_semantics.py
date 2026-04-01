from __future__ import annotations

import numpy as np

from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.model.pose import Pose
from robot_sim.model.trajectory import JointTrajectory


def test_validate_trajectory_separates_goal_error_from_realized_motion():
    t = np.array([0.0, 1.0])
    q = np.zeros((2, 2))
    qd = np.zeros((2, 2))
    qdd = np.zeros((2, 2))
    ee = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    rots = np.repeat(np.eye(3)[None, :, :], 2, axis=0)
    target = Pose(p=np.array([1.2, 0.0, 0.0]), R=np.eye(3))
    traj = JointTrajectory(t=t, q=q, qd=qd, qdd=qdd, ee_positions=ee, ee_rotations=rots)

    report = ValidateTrajectoryUseCase().execute(traj, target_pose=target)

    assert report.start_to_end_position_delta == 1.0
    assert abs(report.goal_position_error - 0.2) < 1.0e-12
    assert report.goal_orientation_error == 0.0
