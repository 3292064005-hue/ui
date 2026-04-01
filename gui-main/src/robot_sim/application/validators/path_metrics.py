from __future__ import annotations

import numpy as np

from robot_sim.core.math.so3 import rotation_error


def evaluate_path_metrics(*, q, qd, qdd, t, ee_positions, ee_rotations) -> dict[str, float]:
    q = np.asarray(q, dtype=float)
    qd = np.asarray(qd, dtype=float)
    qdd = np.asarray(qdd, dtype=float)
    t = np.asarray(t, dtype=float)
    max_velocity = float(np.max(np.abs(qd))) if qd.size else 0.0
    max_acceleration = float(np.max(np.abs(qdd))) if qdd.size else 0.0
    jerk_proxy = 0.0
    if qdd.shape[0] >= 2 and t.size >= 2:
        dt = np.diff(t)
        if dt.size:
            jerk = np.diff(qdd, axis=0) / np.maximum(dt[:, None], 1.0e-12)
            jerk_proxy = float(np.max(np.abs(jerk))) if jerk.size else 0.0
    path_length = 0.0
    start_to_end_position_delta = 0.0
    start_to_end_orientation_delta = 0.0
    if ee_positions is not None and ee_positions.shape[0] >= 2:
        path_length = float(np.sum(np.linalg.norm(np.diff(ee_positions, axis=0), axis=1)))
        start_to_end_position_delta = float(np.linalg.norm(ee_positions[-1] - ee_positions[0]))
    if ee_rotations is not None and ee_rotations.shape[0] >= 2:
        start_to_end_orientation_delta = float(np.linalg.norm(rotation_error(ee_rotations[-1], ee_rotations[0])))
    return {
        'max_velocity': max_velocity,
        'max_acceleration': max_acceleration,
        'jerk_proxy': jerk_proxy,
        'path_length': path_length,
        'start_to_end_position_delta': start_to_end_position_delta,
        'start_to_end_orientation_delta': start_to_end_orientation_delta,
    }
