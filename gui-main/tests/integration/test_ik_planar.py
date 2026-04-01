from __future__ import annotations
import numpy as np
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.math.transforms import rot_z

def test_dls_ik_planar_reachable(planar_spec):
    # 对 2DOF 平面臂，目标姿态必须与末端平面朝向一致，不能强行要求任意 3D 姿态。
    target = Pose(p=np.array([1.2, 1.1, 0.0]), R=rot_z(1.3618395673587185))
    q0 = np.array([0.1, 0.1], dtype=float)
    result = DLSIKSolver().solve(
        planar_spec,
        target,
        q0,
        IKConfig(max_iters=300, damping_lambda=0.1, step_scale=0.4),
    )
    fk = ForwardKinematicsSolver().solve(planar_spec, result.q_sol)
    assert result.success
    assert np.linalg.norm(fk.ee_pose.p[:2] - target.p[:2]) < 1e-3
