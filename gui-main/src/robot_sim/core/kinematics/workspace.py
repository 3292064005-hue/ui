from __future__ import annotations

import numpy as np

from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose


def base_position(spec: RobotSpec) -> np.ndarray:
    return np.asarray(spec.base_T[:3, 3], dtype=float)


def rough_reach_radius(spec: RobotSpec) -> float:
    return float(sum(abs(row.a) + abs(row.d) for row in spec.dh_rows) + np.linalg.norm(spec.tool_T[:3, 3]))


def target_is_certainly_outside_workspace(spec: RobotSpec, target: Pose, *, margin: float = 0.0) -> bool:
    radius = rough_reach_radius(spec)
    distance = float(np.linalg.norm(np.asarray(target.p, dtype=float) - base_position(spec)))
    return distance > radius + float(margin)
