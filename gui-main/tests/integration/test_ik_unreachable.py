from __future__ import annotations
import numpy as np
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.core.ik.dls import DLSIKSolver


def test_dls_ik_unreachable_does_not_crash(planar_spec):
    target = Pose(p=np.array([5.0, 0.0, 0.0]), R=np.eye(3))
    q0 = np.array([0.0, 0.0], dtype=float)
    result = DLSIKSolver().solve(planar_spec, target, q0, IKConfig(max_iters=20))
    assert not result.success
    assert result.message in {
        "max iterations exceeded",
        "cancelled",
        "target outside rough workspace envelope",
    }
    assert result.stop_reason in {"max_iterations", "cancelled", "workspace_precheck"}
