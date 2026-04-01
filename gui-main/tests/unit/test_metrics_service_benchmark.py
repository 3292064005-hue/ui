from __future__ import annotations

from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.model.benchmark_report import BenchmarkReport


def test_metrics_service_summarizes_benchmark_report():
    report = BenchmarkReport(
        robot='Planar',
        num_cases=3,
        success_rate=2/3,
        aggregate={'p95_elapsed_ms': 10.0, 'mean_restarts_used': 1.0},
    )
    summary = MetricsService().summarize_benchmark(report)
    assert summary['robot'] == 'Planar'
    assert summary['num_cases'] == 3
    assert summary['p95_elapsed_ms'] == 10.0
