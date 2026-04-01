from __future__ import annotations
import math
import numpy as np
from robot_sim.model.dh_row import DHRow
from robot_sim.domain.enums import JointType
from robot_sim.domain.types import FloatArray

def dh_transform(row: DHRow, q_value: float) -> FloatArray:
    if row.joint_type is JointType.REVOLUTE:
        theta = row.theta_offset + q_value
        d = row.d
    else:
        theta = row.theta_offset
        d = row.d + q_value
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(row.alpha), math.sin(row.alpha)
    return np.array(
        [
            [ct, -st * ca, st * sa, row.a * ct],
            [st, ct * ca, -ct * sa, row.a * st],
            [0.0, sa, ca, d],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
