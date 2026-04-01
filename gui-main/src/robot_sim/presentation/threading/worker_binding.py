from __future__ import annotations

from typing import Callable

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent, WorkerFinishedEvent
from robot_sim.presentation.threading.task_handle import TaskHandle


class WorkerBindingService:
    """Bind worker/thread signals while keeping orchestration callbacks explicit."""

    def apply_worker_identity(self, worker, task: TaskHandle) -> None:
        """Populate worker identity attributes when they are available.

        Args:
            worker: Worker object that may expose identity attributes.
            task: Canonical orchestrator task handle.

        Returns:
            None: Mutates worker attributes in place.

        Raises:
            None: Missing identity attributes are ignored for compatibility.
        """
        if getattr(worker, 'task_id', None) is not None:
            worker.task_id = task.task_id
        if getattr(worker, 'task_kind', None) is not None:
            worker.task_kind = task.task_kind
        if getattr(worker, 'correlation_id', None) is not None:
            worker.correlation_id = task.correlation_id or task.task_id

    def bind(
        self,
        *,
        worker,
        thread,
        on_started=None,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        progress_event_callback: Callable[[object], None],
        state_changed_callback: Callable[[str], None],
        failed_event_callback: Callable[[WorkerFailedEvent], None],
        finished_event_callback: Callable[[WorkerFinishedEvent], None],
        cancelled_event_callback: Callable[[WorkerCancelledEvent], None],
        failed_callback: Callable[[str], None],
        finished_callback: Callable[[object], None],
        cancelled_callback: Callable[[], None],
        queued_callback: Callable[[], None],
        cleanup_callback: Callable[[], None],
        legacy_progress_adapter: Callable[[object], object] | None = None,
    ) -> None:
        """Bind worker lifecycle signals to orchestrator callbacks.

        Args:
            worker: Background worker exposing the legacy or structured signal set.
            thread: Dedicated worker thread.
            on_started: Optional external start callback.
            on_progress: Optional external progress callback.
            on_finished: Optional external success callback.
            on_failed: Optional external failure callback.
            on_cancelled: Optional external cancellation callback.
            progress_event_callback: Internal callback for structured progress events.
            state_changed_callback: Internal callback for worker state changes.
            failed_event_callback: Internal callback for structured failure events.
            finished_event_callback: Internal callback for structured success events.
            cancelled_event_callback: Internal callback for structured cancellation events.
            failed_callback: Internal callback for legacy failures.
            finished_callback: Internal callback for legacy success payloads.
            cancelled_callback: Internal callback for legacy cancellations.
            queued_callback: Internal callback invoked when the worker starts running.
            cleanup_callback: Cleanup callback invoked after thread shutdown.
            legacy_progress_adapter: Optional adapter translating structured events to legacy progress payloads.

        Returns:
            None: Mutates Qt signal bindings in place.

        Raises:
            None: Binding is side-effect only.
        """
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.started.connect(queued_callback)
        if hasattr(worker, 'failed_event'):
            worker.failed_event.connect(failed_event_callback)
        else:
            worker.failed.connect(failed_callback)
        if hasattr(worker, 'finished_event'):
            worker.finished_event.connect(finished_event_callback)
        else:
            worker.finished.connect(finished_callback)
        if hasattr(worker, 'cancelled_event'):
            worker.cancelled_event.connect(cancelled_event_callback)
        else:
            worker.cancelled.connect(cancelled_callback)
        if hasattr(worker, 'progress_event'):
            worker.progress_event.connect(progress_event_callback)
        if on_progress is not None:
            if hasattr(worker, 'progress'):
                worker.progress.connect(on_progress)
            elif hasattr(worker, 'progress_event'):
                adapter = legacy_progress_adapter or self._coerce_legacy_progress
                worker.progress_event.connect(lambda event: on_progress(adapter(event)))
        if hasattr(worker, 'state_changed'):
            worker.state_changed.connect(state_changed_callback)
        if on_started is not None:
            worker.started.connect(on_started)
        if on_finished is not None:
            worker.finished.connect(on_finished)
        if on_failed is not None:
            worker.failed.connect(on_failed)
        if on_cancelled is not None:
            worker.cancelled.connect(on_cancelled)
        worker.finished.connect(lambda _payload: thread.quit())
        worker.failed.connect(lambda _message: thread.quit())
        worker.cancelled.connect(lambda: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(cleanup_callback)

    @staticmethod
    def _coerce_legacy_progress(event):
        """Translate structured progress events into legacy callback payloads."""
        payload = getattr(event, 'payload', None)
        if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
            return payload['value']
        if payload is not None:
            return payload
        return event
