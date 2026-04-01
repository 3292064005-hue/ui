from __future__ import annotations

import inspect

from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.domain.errors import CancelledTaskError


class BenchmarkWorker(BaseWorker):
    """Qt worker wrapper for benchmark execution."""

    def __init__(self, spec, config, use_case: RunBenchmarkUseCase, cases=None) -> None:
        """Create a benchmark worker.

        Args:
            spec: Robot specification to benchmark.
            config: IK configuration used during benchmarking.
            use_case: Benchmark use case instance.
            cases: Optional benchmark case collection.

        Raises:
            ValueError: If ``use_case`` is not provided.
        """
        super().__init__(task_kind='benchmark')
        if use_case is None:
            raise ValueError('BenchmarkWorker requires an explicit benchmark use case')
        self._spec = spec
        self._config = config
        self._cases = cases
        self._uc = use_case

    @Slot()
    def run(self) -> None:
        """Execute the benchmark use case and emit terminal worker events."""
        self.emit_started()
        try:
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            execute = self._uc.execute
            accepted = set(inspect.signature(execute).parameters)
            kwargs = {}
            if 'cancel_flag' in accepted:
                kwargs['cancel_flag'] = self.is_cancel_requested
            if 'progress_cb' in accepted:
                kwargs['progress_cb'] = lambda percent, message='', payload=None: self.emit_progress(
                    stage='benchmark',
                    percent=float(percent),
                    message=str(message),
                    payload=dict(payload or {}),
                )
            if 'correlation_id' in accepted:
                kwargs['correlation_id'] = self.correlation_id
            report = execute(self._spec, self._config, self._cases, **kwargs)
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(report)
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
