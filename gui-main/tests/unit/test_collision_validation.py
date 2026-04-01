from __future__ import annotations

import numpy as np

from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.model.trajectory import JointTrajectory


def test_validate_trajectory_detects_collision_risk():
    joint_positions = np.array([
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
    ], dtype=float)
    traj = JointTrajectory(
        t=np.array([0.0, 1.0]),
        q=np.zeros((2, 3)),
        qd=np.zeros((2, 3)),
        qdd=np.zeros((2, 3)),
        joint_positions=joint_positions,
        ee_positions=np.array([[0, 0, 0], [1, 0, 0]], dtype=float),
    )
    obstacle = aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0)
    report = ValidateTrajectoryUseCase().execute(traj, collision_obstacles=(obstacle,))
    assert not report.feasible
    assert 'environment_collision_risk' in report.reasons
