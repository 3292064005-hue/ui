from __future__ import annotations

from robot_sim.application.workers.benchmark_worker import BenchmarkWorker
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented


class BenchmarkTaskCoordinator:
    """Own the benchmark task orchestration previously embedded in the window shell."""

    def __init__(self, window, *, runtime=None, benchmark=None, threader=None) -> None:
        self.window = window
        self.runtime = require_dependency(runtime if runtime is not None else getattr(window, 'runtime_facade', None), 'runtime_facade')
        self.benchmark = require_dependency(benchmark if benchmark is not None else getattr(window, 'benchmark_facade', None), 'benchmark_facade')
        self.threader = require_dependency(threader if threader is not None else getattr(window, 'threader', None), 'threader')

    def run(self) -> None:
        self.start_task()

    def start_task(self) -> None:
        def action() -> None:
            spec = self.runtime.state.robot_spec
            if spec is None:
                raise RuntimeError('robot not loaded')
            config = self.benchmark.build_benchmark_config(**require_view(self.window, 'read_solver_kwargs'))
            benchmark_use_case = require_dependency(getattr(self.benchmark, 'benchmark_use_case', None), 'benchmark_facade.benchmark_use_case')
            require_view(self.window, 'project_task_started', 'benchmark', 'Benchmark 已启动')
            task = self.threader.start(
                worker=BenchmarkWorker(spec, config, benchmark_use_case),
                on_finished=self.window.on_benchmark_finished,
                on_failed=self.window.on_worker_failed,
                on_cancelled=self.window.on_worker_cancelled,
                task_kind='benchmark',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title='错误')

    def handle_finished(self, report) -> None:
        require_view(self.window, 'project_busy_state', False, '')

        def action() -> None:
            self.runtime.state_store.patch(benchmark_report=report)
            summary = self.window.metrics_service.summarize_benchmark(report)
            require_view(self.window, 'project_benchmark_result', report, summary)

        run_presented(self.window, action, title='错误')
