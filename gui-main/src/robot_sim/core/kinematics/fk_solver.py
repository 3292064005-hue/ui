from __future__ import annotations

import numpy as np

from robot_sim.core.kinematics.dh import dh_transform
from robot_sim.domain.enums import ReferenceFrame
from robot_sim.domain.types import FloatArray
from robot_sim.model.fk_result import FKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec


class ForwardKinematicsSolver:
    def solve(self, spec: RobotSpec, q: FloatArray) -> FKResult:
        T = np.asarray(spec.base_T, dtype=float).copy()
        T_list = [T.copy()]
        joint_positions = [T[:3, 3].copy()]
        joint_origins = [T[:3, 3].copy()]
        joint_axes = [T[:3, 2].copy()]

        for row, q_i in zip(spec.dh_rows, q):
            T = T @ dh_transform(row, float(q_i))
            T_list.append(T.copy())
            joint_positions.append(T[:3, 3].copy())
            joint_origins.append(T[:3, 3].copy())
            joint_axes.append(T[:3, 2].copy())

        T_ee = T @ np.asarray(spec.tool_T, dtype=float)
        pose = Pose.from_matrix(T_ee, frame=ReferenceFrame.BASE)
        return FKResult(
            T_list=tuple(T_list),
            joint_positions=np.asarray(joint_positions, dtype=float),
            ee_pose=pose,
            joint_axes=np.asarray(joint_axes, dtype=float),
            joint_origins=np.asarray(joint_origins, dtype=float),
            reference_frame=ReferenceFrame.BASE,
            metadata={
                'num_links': int(spec.dof),
                'includes_tool_transform': True,
            },
        )
