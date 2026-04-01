from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.types import FloatArray

def clip_to_joint_limits(spec: RobotSpec, q: FloatArray) -> FloatArray:
    q_out = q.copy()
    for i, row in enumerate(spec.dh_rows):
        q_out[i] = np.clip(q_out[i], row.q_min, row.q_max)
    return q_out
