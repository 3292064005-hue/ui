from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from robot_sim.application.workers.task_events import WorkerCancelledEvent, WorkerFailedEvent, WorkerFinishedEvent
from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.threading import (
    QtThreadRuntimeBridge,
    SubmissionPolicyEngine,
    TaskHandle,
    TaskLifecycleRegistry,
    TimeoutSupervisor,
    WorkerBindingService,
)
from robot_sim.presentation.threading.qt_compat import QObject, QThread, Signal




class _ModuleAwareRuntimeBridge(QtThreadRuntimeBridge):
    """Runtime bridge that preserves module-level QThread monkeypatch compatibility."""

    def create_thread(self):
        """Create a worker thread using the module-level QThread symbol."""
        return QThread()


class ThreadOrchestrator(QObject):  # pragma: no cover - GUI shell
    """Coordinate a single background worker and project structured task state."""

    task_state_changed = Signal(object)

    def __init__(self, parent=None, *, start_policy: str = 'cancel_and_replace'):
        """Initialize the thread orchestrator.

        Args:
            parent: Optional Qt parent object.
            start_policy: Policy used when a new task arrives while one is already active.

        Returns:
            None: Initializes orchestration state.

        Raises:
            None: Construction only initializes internal state.
        """
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._queued_start: dict[str, object] | None = None
        self._lifecycle = TaskLifecycleRegistry(self.task_state_changed.emit)
        self._submission_policy = SubmissionPolicyEngine(start_policy)
        self._timeout_supervisor = TimeoutSupervisor(self)
        self._runtime_bridge = _ModuleAwareRuntimeBridge()
        self._binding_service = WorkerBindingService()
        self.start_policy = str(start_policy)
        self.active_correlation_id: str = ''

    @property
    def worker(self):
        return self._worker

    @property
    def active_task(self) -> TaskHandle | None:
        return self._lifecycle.active_task

    @property
    def active_snapshot(self) -> TaskSnapshot | None:
        return self._lifecycle.last_snapshot

    @property
    def last_terminal_snapshot(self) -> TaskSnapshot | None:
        return self._lifecycle.last_terminal_snapshot

    def is_running(self, *, task_kind: str | None = None) -> bool:
        """Report whether an orchestrated worker is currently active.

        Args:
            task_kind: Optional task family filter.

        Returns:
            bool: ``True`` when a matching active task exists.

        Raises:
            None: The check reads cached in-memory state only.
        """
        if self._thread is None:
            return False
        if task_kind is None or self._lifecycle.active_task is None:
            return True
        return self._lifecycle.active_task.task_kind == str(task_kind)

    def start(
        self,
        worker,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_started=None,
        *,
        task_kind: str = 'generic',
        task_id: str | None = None,
        correlation_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> TaskHandle:
        """Start a worker under the configured orchestration policy.

        Args:
            worker: Worker instance exposing the legacy/structured signal set.
            on_progress: Optional external progress callback.
            on_finished: Optional external finished callback.
            on_failed: Optional external failure callback.
            on_cancelled: Optional external cancellation callback.
            on_started: Optional external started callback.
            task_kind: Logical task family.
            task_id: Optional explicit task identifier.
            correlation_id: Optional correlation identifier.
            timeout_ms: Optional timeout in milliseconds.

        Returns:
            TaskHandle: Handle for the active or queued task.

        Raises:
            RuntimeError: If the configured policy rejects the start request.
        """
        pending = {
            'worker': worker,
            'on_progress': on_progress,
            'on_finished': on_finished,
            'on_failed': on_failed,
            'on_cancelled': on_cancelled,
            'on_started': on_started,
            'task_kind': task_kind,
            'task_id': task_id,
            'correlation_id': correlation_id,
            'timeout_ms': timeout_ms,
        }
        task = TaskHandle(
            task_id=str(task_id or getattr(worker, 'task_id', str(uuid4())) or str(uuid4())),
            task_kind=str(task_kind),
            correlation_id=str(correlation_id or getattr(worker, 'correlation_id', '') or task_id or ''),
        )
        decision = self._submission_policy.decide(is_running=self.is_running())
        if decision == 'reject':
            raise RuntimeError('task already running')
        if decision == 'queue_latest':
            self._queued_start = dict(pending)
            self._binding_service.apply_worker_identity(worker, task)
            return task
        if decision == 'cancel_and_replace':
            replaced_task_id = self._lifecycle.current_task_id()
            self._lifecycle.mark_terminal_locked(replaced_task_id)
            self.stop(wait=False, stop_reason='replaced')
        return self._start_now(task=task, **pending)

    def _start_now(
        self,
        *,
        task: TaskHandle,
        worker,
        on_progress=None,
        on_finished=None,
        on_failed=None,
        on_cancelled=None,
        on_started=None,
        task_kind: str = 'generic',
        task_id: str | None = None,
        correlation_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> TaskHandle:
        """Wire a worker into a dedicated thread and start execution."""
        del task_kind, task_id, correlation_id
        thread = self._runtime_bridge.create_thread()
        self._binding_service.apply_worker_identity(worker, task)
        self._thread = thread
        self._worker = worker
        self._lifecycle.begin(task)
        self.active_correlation_id = self._lifecycle.active_task.correlation_id if self._lifecycle.active_task else ''
        self._timeout_supervisor.cancel()
        self._set_state(TaskState.QUEUED, message='queued')
        self._binding_service.bind(
            worker=worker,
            thread=thread,
            on_started=on_started,
            on_progress=on_progress,
            on_finished=on_finished,
            on_failed=on_failed,
            on_cancelled=on_cancelled,
            progress_event_callback=self._on_progress_event,
            state_changed_callback=self._on_state_changed,
            failed_event_callback=self._handle_failed_event,
            finished_event_callback=self._handle_finished_event,
            cancelled_event_callback=self._handle_cancelled_event,
            failed_callback=self._handle_failed,
            finished_callback=self._handle_finished,
            cancelled_callback=self._handle_cancelled,
            queued_callback=lambda: self._set_state(TaskState.RUNNING, message='running'),
            cleanup_callback=self._cleanup,
        )
        self._runtime_bridge.start(thread)
        self._timeout_supervisor.arm(timeout_ms, task_id=task.task_id, callback=self._on_timeout)
        return self._lifecycle.active_task

    def cancel(self) -> None:
        """Request cooperative cancellation from the active worker."""
        if self._worker is not None:
            self._set_state(TaskState.CANCELLING, message='cancelling')
            self._worker.request_cancel()

    def stop(self, wait: bool = True, *, stop_reason: str = 'cancelled') -> None:
        """Stop the active worker thread.

        Args:
            wait: Whether to block until the worker thread exits.
            stop_reason: Stop reason propagated to task snapshots when possible.

        Returns:
            None: Requests worker/thread shutdown and performs cleanup.

        Raises:
            None: Safe to call when no active task exists.
        """
        if self._thread is None:
            return
        if self._worker is not None:
            self._set_state(TaskState.CANCELLING, message='cancelling', stop_reason=stop_reason)
            self._worker.request_cancel()
        self._runtime_bridge.stop(self._thread, wait=wait)
        self._cleanup()

    def _on_progress_event(self, event) -> None:
        self._set_state(
            TaskState.RUNNING,
            stage=getattr(event, 'stage', ''),
            percent=float(getattr(event, 'percent', 0.0) or 0.0),
            message=str(getattr(event, 'message', '')),
        )

    @staticmethod
    def _coerce_legacy_progress(event):
        payload = getattr(event, 'payload', None)
        if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
            return payload['value']
        if payload is not None:
            return payload
        return event

    def _on_state_changed(self, state: str) -> None:
        if state not in {item.value for item in TaskState}:
            return
        self._set_state(TaskState(state), message=state)

    def _handle_failed(self, message: str) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(TaskState.FAILED, message=str(message), stop_reason='exception', finished=True)

    def _handle_failed_event(self, event: WorkerFailedEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.FAILED,
            message=str(getattr(event, 'message', '')),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'exception'),
            finished=True,
        )

    def _handle_finished(self, _payload) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(TaskState.SUCCEEDED, message='completed', stop_reason='completed', finished=True)

    def _handle_finished_event(self, event: WorkerFinishedEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.SUCCEEDED,
            message=str(getattr(event, 'stop_reason', '') or 'completed'),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'completed'),
            finished=True,
            finished_at=getattr(event, 'finished_at', None),
        )

    def _handle_cancelled(self) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(TaskState.CANCELLED, message='cancelled', stop_reason='cancelled', finished=True)

    def _handle_cancelled_event(self, event: WorkerCancelledEvent) -> None:
        if self._lifecycle.is_terminal_locked():
            return
        self._set_state(
            TaskState.CANCELLED,
            message=str(getattr(event, 'message', '') or 'cancelled'),
            stop_reason=str(getattr(event, 'stop_reason', '') or 'cancelled'),
            finished=True,
            finished_at=getattr(event, 'finished_at', None),
        )

    def _on_timeout(self, task_id: str) -> None:
        if self._lifecycle.active_task is None or self._lifecycle.active_task.task_id != str(task_id):
            return
        self._lifecycle.mark_terminal_locked(task_id)
        self._set_state(TaskState.CANCELLED, message='timeout', stop_reason='timeout', finished=True)
        if self._worker is not None:
            self._worker.request_cancel()
            if hasattr(self._worker, 'emit_cancelled'):
                self._worker.emit_cancelled(stop_reason='timeout', message='timeout')
        if self._thread is not None:
            self._runtime_bridge.stop(self._thread, wait=False)

    def _set_state(
        self,
        state: TaskState,
        *,
        stage: str = '',
        percent: float = 0.0,
        message: str = '',
        stop_reason: str = '',
        finished: bool = False,
        finished_at: datetime | None = None,
    ) -> None:
        self._lifecycle.set_state(
            state,
            stage=stage,
            percent=percent,
            message=message,
            stop_reason=stop_reason,
            finished=finished,
            finished_at=finished_at,
        )

    def _cleanup(self) -> None:
        """Reset transient runtime state and start any queued replacement task."""
        self._timeout_supervisor.cancel()
        self._thread = None
        self._worker = None
        self.active_correlation_id = ''
        self._lifecycle.reset_runtime()
        queued = self._queued_start
        self._queued_start = None
        if queued:
            self.start(**queued)
