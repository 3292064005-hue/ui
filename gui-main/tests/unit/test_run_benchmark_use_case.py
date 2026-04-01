from __future__ import annotations

from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.solver_config import IKConfig


def test_run_benchmark_use_case_returns_report(planar_spec):
    report = RunBenchmarkUseCase(BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))).execute(planar_spec, IKConfig(position_only=True, retry_count=1))
    assert report.robot == planar_spec.label
    assert report.num_cases >= 5
    assert 0.0 <= report.success_rate <= 1.0
    assert 'p95_elapsed_ms' in report.aggregate
