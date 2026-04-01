from __future__ import annotations

from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry, SolverRegistry


def test_default_solver_registry_exposes_expected_ids():
    reg = DefaultSolverRegistry()
    assert reg.ids() == ['analytic_6r', 'dls', 'lm', 'pinv']


def test_run_ik_uses_custom_solver_registry(planar_spec):
    class DummySolver:
        def solve(self, spec, target, q0, config, **kwargs):
            from robot_sim.model.ik_result import IKResult
            return IKResult(True, q0.copy(), tuple(), 'dummy', effective_mode='dummy')

    reg = SolverRegistry()
    reg.register('dls', DummySolver())
    uc = RunIKUseCase(reg)
    assert uc.solver_ids == ['dls']
