from __future__ import annotations

from robot_sim.application.services.export_service import ExportService
from robot_sim.model.benchmark_report import BenchmarkReport


def test_export_service_writes_benchmark_cases_csv(tmp_path):
    exporter = ExportService(tmp_path)
    report = BenchmarkReport(
        robot='Planar',
        num_cases=1,
        success_rate=1.0,
        cases=({'name': 'case1', 'success': True, 'stop_reason': 'converged'},),
    )
    path = exporter.save_benchmark_cases_csv('cases.csv', report)
    text = path.read_text(encoding='utf-8')
    assert 'case1' in text
    assert 'stop_reason' in text
