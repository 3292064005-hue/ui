from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import SolverRegistry
from robot_sim.model.ik_result import IKResult
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


class _CaptureSolver:
    def __init__(self) -> None:
        self.last_request = None
        self.calls = 0

    def solve(self, spec, target, q0, config, **kwargs):
        self.calls += 1
        self.last_request = {'target': target, 'q0': np.asarray(q0, dtype=float).copy(), 'config': config}
        if self.calls == 1 and not bool(config.position_only):
            return IKResult(
                False,
                np.asarray(q0, dtype=float).copy(),
                tuple(),
                'orientation mismatch',
                final_pos_err=1.0e-4,
                final_ori_err=0.25,
                stop_reason='orientation_not_satisfied',
                best_q=np.asarray(q0, dtype=float).copy(),
                diagnostics={},
            )
        return IKResult(
            True,
            np.asarray(q0, dtype=float).copy(),
            tuple(),
            'converged',
            final_pos_err=1.0e-5,
            final_ori_err=0.0,
            stop_reason='converged',
            best_q=np.asarray(q0, dtype=float).copy(),
            diagnostics={},
        )


def test_joint_limit_seed_adapter_clamps_seed(planar_spec):
    solver = _CaptureSolver()
    reg = SolverRegistry()
    reg.register('dls', solver)
    uc = RunIKUseCase(reg)
    target = Pose(p=np.array([1.5, 0.0, 0.0], dtype=float), R=np.eye(3, dtype=float))
    req = IKRequest(
        spec=planar_spec,
        target=target,
        q0=np.array([10.0, -10.0], dtype=float),
        config=IKConfig(clamp_seed_to_joint_limits=True),
    )
    result = uc.execute(req)
    q0_used = solver.last_request['q0']
    mins = np.array([row.q_min for row in planar_spec.dh_rows], dtype=float)
    maxs = np.array([row.q_max for row in planar_spec.dh_rows], dtype=float)
    assert np.all(q0_used <= maxs + 1.0e-9)
    assert np.all(q0_used >= mins - 1.0e-9)
    adapter_ids = [item['adapter_id'] for item in result.diagnostics['request_adapters']]
    assert 'joint_limit_seed_clamp' in adapter_ids


def test_target_rotation_is_normalized_before_solver(planar_spec):
    solver = _CaptureSolver()
    reg = SolverRegistry()
    reg.register('dls', solver)
    uc = RunIKUseCase(reg)
    skewed_R = np.eye(3, dtype=float)
    skewed_R[0, 1] = 1.0e-3
    target = Pose(p=np.array([1.0, 0.0, 0.0], dtype=float), R=skewed_R)
    req = IKRequest(spec=planar_spec, target=target, q0=np.zeros(2, dtype=float), config=IKConfig())
    result = uc.execute(req)
    normalized = solver.last_request['target'].R
    assert np.allclose(normalized.T @ normalized, np.eye(3, dtype=float), atol=1.0e-8)
    adapter_ids = [item['adapter_id'] for item in result.diagnostics['request_adapters']]
    assert 'target_rotation_normalization' in adapter_ids


def test_orientation_relaxation_adapter_retries_in_position_only(planar_spec):
    solver = _CaptureSolver()
    reg = SolverRegistry()
    reg.register('dls', solver)
    uc = RunIKUseCase(reg)
    req = IKRequest(
        spec=planar_spec,
        target=Pose(p=np.array([1.0, 0.0, 0.0], dtype=float), R=np.eye(3, dtype=float)),
        q0=np.zeros(2, dtype=float),
        config=IKConfig(allow_orientation_relaxation=True),
    )
    result = uc.execute(req)
    assert result.success
    assert result.stop_reason == 'orientation_relaxed_converged'
    assert solver.calls == 2
    adapter_ids = [item['adapter_id'] for item in result.diagnostics['request_adapters']]
    assert 'orientation_relaxation_fallback' in adapter_ids
