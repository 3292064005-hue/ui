from __future__ import annotations

from robot_sim.application.services.export_service import ExportService
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.state_store import StateStore


def test_export_controller_exports_benchmark_json(tmp_path):
    state = StateStore(SessionState(benchmark_report=BenchmarkReport(robot='Planar', num_cases=1, success_rate=1.0)))
    exporter = ExportService(tmp_path)
    controller = ExportController(state, exporter, ExportReportUseCase(exporter), SaveSessionUseCase(exporter))
    path = controller.export_benchmark('bench.json')
    assert path.exists()
