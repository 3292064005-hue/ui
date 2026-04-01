from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class Pose:
    p: FloatArray
    R: FloatArray
    frame: ReferenceFrame = ReferenceFrame.BASE

    @staticmethod
    def from_matrix(T: FloatArray, *, frame: ReferenceFrame = ReferenceFrame.BASE) -> "Pose":
        return Pose(p=T[:3, 3].copy(), R=T[:3, :3].copy(), frame=frame)

    def to_matrix(self) -> FloatArray:
        T = np.eye(4, dtype=float)
        T[:3, :3] = self.R
        T[:3, 3] = self.p
        return T

    def with_frame(self, frame: ReferenceFrame) -> "Pose":
        return Pose(p=np.asarray(self.p, dtype=float).copy(), R=np.asarray(self.R, dtype=float).copy(), frame=frame)
