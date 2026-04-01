from __future__ import annotations

import numpy as np

from robot_sim.core.math.so3 import rotation_error


def evaluate_goal_metrics(*, ee_positions, ee_rotations, target_pose) -> dict[str, float]:
    goal_position_error = 0.0
    goal_orientation_error = 0.0
    if target_pose is not None:
        if ee_positions is not None and ee_positions.shape[0] >= 1:
            goal_position_error = float(np.linalg.norm(ee_positions[-1] - np.asarray(target_pose.p, dtype=float)))
        if ee_rotations is not None and ee_rotations.shape[0] >= 1:
            goal_orientation_error = float(np.linalg.norm(rotation_error(np.asarray(target_pose.R, dtype=float), ee_rotations[-1])))
    return {'goal_position_error': goal_position_error, 'goal_orientation_error': goal_orientation_error}
