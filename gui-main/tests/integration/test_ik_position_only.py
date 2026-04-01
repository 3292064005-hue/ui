from __future__ import annotations
import numpy as np
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.pose import Pose
from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver


def test_position_only_ik_ignores_unreachable_orientation(planar_spec):
    solver = DLSIKSolver()
    q0 = np.array([0.0, 0.0], dtype=float)
    target = Pose(
        p=np.array([1.2, 1.1, 0.0], dtype=float),
        R=np.eye(3, dtype=float),
    )
    result = solver.solve(
        planar_spec,
        target,
        q0,
        IKConfig(max_iters=250, damping_lambda=0.05, step_scale=0.6, position_only=True),
    )
    fk = ForwardKinematicsSolver().solve(planar_spec, result.q_sol)
    assert result.success
    assert np.linalg.norm(fk.ee_pose.p - target.p) < 1e-2
