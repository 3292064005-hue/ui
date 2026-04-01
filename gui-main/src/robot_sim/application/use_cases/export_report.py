from __future__ import annotations

from pathlib import Path

from robot_sim.application.mappers import benchmark_report_to_dict
from robot_sim.application.services.export_service import ExportService
from robot_sim.model.benchmark_report import BenchmarkReport


class ExportReportUseCase:
    def __init__(self, exporter: ExportService) -> None:
        self._exporter = exporter

    def benchmark_json(self, name: str, report: BenchmarkReport) -> Path:
        return self._exporter.save_benchmark_report(name, benchmark_report_to_dict(report))

    def metrics_json(self, name: str, metrics: dict) -> Path:
        return self._exporter.save_metrics(name, metrics)
