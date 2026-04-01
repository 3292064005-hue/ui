from __future__ import annotations

import inspect

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.domain.errors import CancelledTaskError


class TrajectoryWorker(BaseWorker):
    """Qt worker wrapper for the trajectory planning use case."""

    def __init__(self, request: TrajectoryRequest, use_case: PlanTrajectoryUseCase) -> None:
        """Create a trajectory worker.

        Args:
            request: Immutable trajectory planning request.
            use_case: Planning use case invoked on the worker thread.

        Raises:
            ValueError: If ``use_case`` is not provided.
        """
        super().__init__(task_kind='trajectory')
        if use_case is None:
            raise ValueError('TrajectoryWorker requires an explicit trajectory use case')
        self._request = request
        self._use_case = use_case

    @Slot()
    def run(self) -> None:
        """Execute the planning use case and emit terminal worker events."""
        self.emit_started()
        try:
            execute = self._use_case.execute
            accepted = set(inspect.signature(execute).parameters)
            kwargs = {}
            if 'cancel_flag' in accepted:
                kwargs['cancel_flag'] = self.is_cancel_requested
            if 'progress_cb' in accepted:
                kwargs['progress_cb'] = lambda percent, message='', payload=None: self.emit_progress(
                    stage='trajectory',
                    percent=float(percent),
                    message=str(message),
                    payload=dict(payload or {}),
                )
            if 'correlation_id' in accepted:
                kwargs['correlation_id'] = self.correlation_id
            result = execute(self._request, **kwargs)
            if self.is_cancel_requested():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(result, metadata={'planner_id': getattr(result, 'metadata', {}).get('planner_id', '')})
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
