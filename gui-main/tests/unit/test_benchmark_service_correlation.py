from __future__ import annotations

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.solver_config import IKConfig


def test_benchmark_service_includes_correlation_id(planar_spec):
    service = BenchmarkService(RunIKUseCase(DefaultSolverRegistry()))
    report = service.run(planar_spec, IKConfig(position_only=True, retry_count=1), correlation_id="corr-bench")
    assert report["metadata"]["correlation_id"] == "corr-bench"
    assert report["metadata"]["suite_metadata"]["correlation_id"] == "corr-bench"
