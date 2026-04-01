from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray
from robot_sim.model.pose import Pose


@dataclass(frozen=True)
class FKResult:
    T_list: tuple[FloatArray, ...]
    joint_positions: FloatArray
    ee_pose: Pose
    joint_axes: FloatArray | None = None
    joint_origins: FloatArray | None = None
    reference_frame: ReferenceFrame = ReferenceFrame.BASE
    metadata: dict[str, object] = field(default_factory=dict)
