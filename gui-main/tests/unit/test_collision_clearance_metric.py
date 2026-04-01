from __future__ import annotations

import numpy as np

from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.model.trajectory import JointTrajectory


def test_validate_trajectory_reports_positive_clearance_when_scene_is_separated():
    joint_positions = np.array(
        [
            [[0, 0, 0], [0.5, 0, 0], [1.0, 0, 0]],
            [[0, 0, 0], [0.5, 0.1, 0], [1.0, 0.2, 0]],
        ],
        dtype=float,
    )
    traj = JointTrajectory(
        t=np.array([0.0, 1.0]),
        q=np.zeros((2, 2)),
        qd=np.zeros((2, 2)),
        qdd=np.zeros((2, 2)),
        joint_positions=joint_positions,
        ee_positions=np.array([[1.0, 0.0, 0.0], [1.0, 0.2, 0.0]], dtype=float),
    )
    obstacle = aabb_from_points(np.array([[2.0, 2.0, -0.1], [2.2, 2.2, 0.1]], dtype=float), padding=0.0)
    report = ValidateTrajectoryUseCase().execute(traj, collision_obstacles=(obstacle,))
    assert report.feasible
    assert report.metadata['collision_summary']['clearance_metric'] > 0.0
