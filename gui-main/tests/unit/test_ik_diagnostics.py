from __future__ import annotations

import numpy as np

from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


def test_dls_ik_reports_adaptive_damping(planar_spec):
    target = Pose(p=np.array([1.6, 0.2, 0.0]), R=np.eye(3))
    result = DLSIKSolver().solve(
        planar_spec,
        target,
        planar_spec.home_q.copy(),
        IKConfig(position_only=True, adaptive_damping=True, use_weighted_least_squares=True, retry_count=0),
    )
    assert result.logs
    assert result.logs[0].damping_lambda >= 1.0e-4
    assert 'damping_lambda' in result.diagnostics


def test_dls_ik_reports_workspace_precheck(planar_spec):
    target = Pose(p=np.array([100.0, 0.0, 0.0]), R=np.eye(3))
    result = DLSIKSolver().solve(
        planar_spec,
        target,
        planar_spec.home_q.copy(),
        IKConfig(position_only=True, reachability_precheck=True),
    )
    assert result.success is False
    assert result.stop_reason == 'workspace_precheck'
    assert result.diagnostics['workspace_radius'] > 0.0
