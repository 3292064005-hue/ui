from __future__ import annotations
from dataclasses import dataclass
from robot_sim.domain.enums import JointType

@dataclass(frozen=True)
class DHRow:
    a: float
    alpha: float
    d: float
    theta_offset: float
    joint_type: JointType
    q_min: float
    q_max: float
