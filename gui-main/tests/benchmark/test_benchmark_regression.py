from __future__ import annotations

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.solver_config import IKConfig


def test_benchmark_service_compares_against_baseline(planar_spec):
    service = BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))
    baseline = {'success_rate': 0.95, 'aggregate': {'p95_elapsed_ms': 50.0}}
    report = service.run(planar_spec, IKConfig(), baseline=baseline)
    assert 'comparison' in report
    assert 'regressed' in report['comparison']
