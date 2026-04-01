from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import SolverRegistry
from robot_sim.domain.enums import IKSolverMode
from robot_sim.model.ik_result import IKResult
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


class _FakeSolver:
    def solve(self, spec, target, q0, config, cancel_flag=None, progress_cb=None, attempt_idx: int = 0):
        if np.allclose(q0, spec.home_q):
            return IKResult(
                True,
                np.asarray(q0, dtype=float).copy(),
                tuple(),
                'converged',
                final_pos_err=0.0,
                final_ori_err=0.0,
                stop_reason='converged',
            )
        return IKResult(
            False,
            np.asarray(q0, dtype=float).copy(),
            tuple(),
            'max iterations exceeded',
            final_pos_err=1.0,
            final_ori_err=1.0,
            stop_reason='max_iterations',
        )


def test_run_ik_use_case_retries_alternative_seed(planar_spec):
    req = IKRequest(
        spec=planar_spec,
        target=Pose(p=np.array([1.0, 0.5, 0.0]), R=np.eye(3)),
        q0=np.array([0.8, -0.8]),
        config=IKConfig(mode=IKSolverMode.DLS, retry_count=2),
    )
    reg = SolverRegistry()
    reg.register(IKSolverMode.DLS.value, _FakeSolver())
    reg.register(IKSolverMode.PINV.value, _FakeSolver())
    uc = RunIKUseCase(reg)
    result = uc.execute(req)
    assert result.success is True
    assert result.restarts_used >= 1
    assert np.allclose(result.q_sol, planar_spec.home_q)
