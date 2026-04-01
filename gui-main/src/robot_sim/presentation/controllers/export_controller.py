from __future__ import annotations

from pathlib import Path

from robot_sim.application.services.export_service import ExportService
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.presentation.state_store import StateStore


class ExportController:
    """Presentation-facing export facade."""

    def __init__(self, state_store: StateStore, exporter: ExportService, export_report_uc: ExportReportUseCase, save_session_uc: SaveSessionUseCase, export_package_uc: ExportPackageUseCase | None = None) -> None:
        self._state_store = state_store
        self._exporter = exporter
        self._export_report_uc = export_report_uc
        self._save_session_uc = save_session_uc
        self._export_package_uc = export_package_uc

    def export_trajectory(self, name: str = 'trajectory.csv'):
        """Export the active trajectory bundle using canonical manifest metadata."""
        traj = self._state_store.state.trajectory
        if traj is None:
            raise RuntimeError('trajectory not available')
        robot_id = self._state_store.state.robot_spec.name if self._state_store.state.robot_spec is not None else None
        solver_id = self._state_store.state.ik_result.effective_mode if self._state_store.state.ik_result is not None else None
        planner_id = resolve_planner_metadata(traj.metadata)['planner_id']
        return self._exporter.save_trajectory_bundle(name, traj, robot_id=robot_id, solver_id=solver_id, planner_id=planner_id)

    def export_trajectory_metrics(self, name: str, metrics: dict):
        """Export trajectory metrics as JSON."""
        return self._export_report_uc.metrics_json(name, metrics)

    def export_benchmark(self, name: str = 'benchmark_report.json'):
        """Export the active benchmark summary JSON."""
        report = self._state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        return self._export_report_uc.benchmark_json(name, report)

    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv'):
        """Export benchmark case rows as CSV."""
        report = self._state_store.state.benchmark_report
        if report is None:
            raise RuntimeError('benchmark report not available')
        return self._exporter.save_benchmark_cases_csv(name, report)

    def export_session(self, name: str = 'session.json'):
        """Export the active session snapshot."""
        return self._save_session_uc.execute(name, self._state_store.state)

    def export_package(self, name: str = 'robot_sim_package.zip') -> Path:
        """Export the currently available artifacts as a package bundle."""
        if self._export_package_uc is None:
            raise RuntimeError('package export not configured')
        files: list[Path] = []
        if self._state_store.state.trajectory is not None:
            files.append(self.export_trajectory('trajectory_bundle.npz'))
        if self._state_store.state.benchmark_report is not None:
            files.append(self.export_benchmark('benchmark_report.json'))
            files.append(self.export_benchmark_cases_csv('benchmark_cases.csv'))
        files.append(self.export_session('session.json'))
        if not files:
            raise RuntimeError('nothing to export')
        robot_id = self._state_store.state.robot_spec.name if self._state_store.state.robot_spec is not None else None
        solver_id = self._state_store.state.ik_result.effective_mode if self._state_store.state.ik_result is not None else None
        planner_id = None
        if self._state_store.state.trajectory is not None:
            planner_id = resolve_planner_metadata(self._state_store.state.trajectory.metadata)['planner_id']
        return self._export_package_uc.execute(name, files, robot_id=robot_id, solver_id=solver_id, planner_id=planner_id)
