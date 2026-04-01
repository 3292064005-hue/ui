from __future__ import annotations

from robot_sim.application.services.export_service import ExportService
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.model.benchmark_report import BenchmarkReport


def test_export_report_use_case_writes_benchmark_json(tmp_path):
    exporter = ExportService(tmp_path)
    uc = ExportReportUseCase(exporter)
    report = BenchmarkReport(
        robot='Planar',
        num_cases=2,
        success_rate=0.5,
        cases=({'name': 'a', 'success': True}, {'name': 'b', 'success': False}),
        aggregate={'p95_elapsed_ms': 12.0},
    )
    path = uc.benchmark_json('bench.json', report)
    assert path.exists()
    assert 'bench.json' in path.name
