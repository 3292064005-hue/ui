from __future__ import annotations

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented


class ExportTaskCoordinator:
    """Own export orchestration for the main window."""

    def __init__(self, window, *, runtime=None, export=None) -> None:
        self.window = window
        self.runtime = require_dependency(runtime if runtime is not None else getattr(window, 'runtime_facade', None), 'runtime_facade')
        self.export = require_dependency(export if export is not None else getattr(window, 'export_facade', None), 'export_facade')

    def export_trajectory(self) -> None:
        def action() -> None:
            path = self.export.export_trajectory()
            metrics = self.window.metrics_service.summarize_trajectory(self.runtime.state.trajectory)
            metrics_path = self.export.export_trajectory_metrics('trajectory_metrics.json', metrics)
            require_view(self.window, 'project_export_messages', f'轨迹已导出：{path}', f'轨迹指标已导出：{metrics_path}')

        run_presented(self.window, action, title='导出失败')

    def export_session(self) -> None:
        def action() -> None:
            path = self.export.export_session()
            require_view(self.window, 'project_export_messages', f'会话已导出：{path}')

        run_presented(self.window, action, title='导出失败')

    def export_package(self) -> None:
        def action() -> None:
            path = self.export.export_package()
            require_view(self.window, 'project_export_messages', f'完整导出包已生成：{path}')

        run_presented(self.window, action, title='导出失败')

    def export_benchmark(self) -> None:
        def action() -> None:
            json_path = self.export.export_benchmark()
            csv_path = self.export.export_benchmark_cases_csv()
            require_view(self.window, 'project_export_messages', f'Benchmark 报告已导出：{json_path}', f'Benchmark 明细已导出：{csv_path}')

        run_presented(self.window, action, title='导出失败')
