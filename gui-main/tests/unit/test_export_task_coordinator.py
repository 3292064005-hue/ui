from types import SimpleNamespace

from robot_sim.presentation.coordinators.export_task_coordinator import ExportTaskCoordinator


class DummyWindow:
    def __init__(self):
        self.controller = SimpleNamespace(
            export_trajectory=lambda: 'trajectory.csv',
            export_trajectory_metrics=lambda _name, _metrics: 'trajectory_metrics.json',
            export_session=lambda: 'session.json',
            export_package=lambda: 'package.zip',
            export_benchmark=lambda: 'benchmark.json',
            export_benchmark_cases_csv=lambda: 'benchmark.csv',
            state=SimpleNamespace(trajectory=SimpleNamespace()),
        )
        self.runtime_facade = SimpleNamespace(state=SimpleNamespace(trajectory=SimpleNamespace()))
        self.export_facade = SimpleNamespace(
            export_trajectory=lambda: 'trajectory.csv',
            export_trajectory_metrics=lambda _name, _metrics: 'trajectory_metrics.json',
            export_session=lambda: 'session.json',
            export_package=lambda: 'package.zip',
            export_benchmark=lambda: 'benchmark.json',
            export_benchmark_cases_csv=lambda: 'benchmark.csv',
        )
        self.metrics_service = SimpleNamespace(summarize_trajectory=lambda _traj: {'mode': 'joint'})
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.project_export_messages = lambda *messages: [self.status_panel.append(message) for message in messages]
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))


def test_export_task_coordinator_exports_all_supported_artifacts():
    window = DummyWindow()
    coord = ExportTaskCoordinator(window)
    coord.export_trajectory()
    coord.export_session()
    coord.export_package()
    coord.export_benchmark()
    assert window.status_panel.messages == [
        '轨迹已导出：trajectory.csv',
        '轨迹指标已导出：trajectory_metrics.json',
        '会话已导出：session.json',
        '完整导出包已生成：package.zip',
        'Benchmark 报告已导出：benchmark.json',
        'Benchmark 明细已导出：benchmark.csv',
    ]
