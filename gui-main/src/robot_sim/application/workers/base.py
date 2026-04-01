from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Mapping
from uuid import uuid4

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtCore import QObject, Signal, Slot
else:
    try:
        from PySide6.QtCore import QObject, Signal, Slot
    except Exception:  # pragma: no cover
        class QObject:
            def __init__(self, *args, **kwargs):
                super().__init__()

            def moveToThread(self, _thread) -> None:
                return None

            def deleteLater(self) -> None:
                return None

        def Slot(*args, **kwargs):
            def deco(fn):
                return fn
            return deco

        class _DummySignalInstance:
            def __init__(self) -> None:
                self._callbacks: list[object] = []

            def emit(self, *args, **kwargs) -> None:
                for cb in list(self._callbacks):
                    cb(*args, **kwargs)

            def connect(self, callback, *args, **kwargs) -> None:
                self._callbacks.append(callback)

        class Signal:
            def __init__(self, *args, **kwargs) -> None:
                self._name = ''

            def __set_name__(self, owner, name) -> None:
                self._name = f'__signal_{name}'

            def __get__(self, instance, owner):
                if instance is None:
                    return self
                signal = instance.__dict__.get(self._name)
                if signal is None:
                    signal = _DummySignalInstance()
                    instance.__dict__[self._name] = signal
                return signal

from robot_sim.application.workers.task_events import (
    WorkerCancelledEvent,
    WorkerFailedEvent,
    WorkerFinishedEvent,
    WorkerProgressEvent,
)
from robot_sim.domain.enums import TaskState
from robot_sim.domain.errors import CancelledTaskError, RobotSimError


class BaseWorker(QObject):
    """Qt worker base class with structured lifecycle events.

    The worker keeps the legacy Qt signals for backward compatibility while
    emitting structured event objects for richer orchestration and diagnostics.
    """

    started = Signal()
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    state_changed = Signal(str)
    progress_event = Signal(object)
    finished_event = Signal(object)
    failed_event = Signal(object)
    cancelled_event = Signal(object)

    _TERMINAL_STATES = {
        TaskState.SUCCEEDED.value,
        TaskState.FAILED.value,
        TaskState.CANCELLED.value,
    }

    def __init__(self, *, task_kind: str = 'generic', task_id: str | None = None, correlation_id: str | None = None) -> None:
        """Initialize the worker identity and lifecycle state.

        Args:
            task_kind: Stable task family name used for routing and UI display.
            task_id: Optional externally assigned task identifier.
            correlation_id: Optional correlation identifier propagated through logs.
        """
        super().__init__()
        self._cancel_requested = False
        self._state = TaskState.IDLE.value
        self.task_kind = str(task_kind)
        self.task_id = str(task_id or uuid4())
        self.correlation_id = str(correlation_id or self.task_id)

    @property
    def state(self) -> str:
        """Return the current worker lifecycle state."""
        return self._state

    def _set_state(self, state: str) -> None:
        """Update the worker lifecycle state.

        Args:
            state: New state value aligned with :class:`robot_sim.domain.enums.TaskState`.
        """
        next_state = str(state)
        if self._state in self._TERMINAL_STATES and next_state not in self._TERMINAL_STATES:
            return
        if self._state == next_state:
            return
        self._state = next_state
        self.state_changed.emit(self._state)

    def request_cancel(self) -> None:
        """Request cooperative cancellation.

        The call is idempotent and will not move an already terminal worker back
        into the cancelling state.
        """
        if self._state in self._TERMINAL_STATES:
            return
        self._cancel_requested = True
        if self._state != TaskState.CANCELLING.value:
            self._set_state(TaskState.CANCELLING.value)

    def reset_cancel(self) -> None:
        """Clear cancellation state for test helpers or worker reuse."""
        self._cancel_requested = False
        if self._state not in self._TERMINAL_STATES:
            self._set_state(TaskState.IDLE.value)

    def is_cancel_requested(self) -> bool:
        """Return whether cooperative cancellation has been requested."""
        return self._cancel_requested

    def is_cancelled(self) -> bool:
        """Backward-compatible alias for :meth:`is_cancel_requested`."""
        return self.is_cancel_requested()

    def emit_started(self) -> None:
        """Emit the worker started lifecycle transition."""
        self._set_state(TaskState.RUNNING.value)
        self.started.emit()

    def emit_progress(self, stage: str = '', percent: float = 0.0, message: str = '', payload: dict[str, object] | None = None) -> None:
        """Emit structured and legacy progress notifications.

        Args:
            stage: Progress stage name.
            percent: Progress percentage in the ``[0, 100]`` range.
            message: User-facing progress message.
            payload: Optional structured payload.
        """
        event = WorkerProgressEvent(
            task_id=self.task_id,
            task_kind=self.task_kind,
            stage=str(stage),
            percent=float(percent),
            message=str(message),
            correlation_id=self.correlation_id,
            payload=dict(payload or {}),
        )
        self.progress_event.emit(event)
        legacy_payload: object = event
        if payload is not None and 'value' in payload and len(payload) == 1:
            legacy_payload = payload['value']
        elif payload:
            legacy_payload = payload
        self.progress.emit(legacy_payload)

    def emit_finished(self, payload: object, stop_reason: str = 'completed', *, metadata: Mapping[str, object] | None = None) -> None:
        """Emit structured and legacy success notifications.

        Args:
            payload: Task result payload.
            stop_reason: Terminal stop reason.
            metadata: Optional structured metadata associated with the result.
        """
        self._set_state(TaskState.SUCCEEDED.value)
        event = WorkerFinishedEvent(
            task_id=self.task_id,
            task_kind=self.task_kind,
            correlation_id=self.correlation_id,
            stop_reason=str(stop_reason),
            payload=payload,
            metadata=dict(metadata or {}),
            finished_at=datetime.now(timezone.utc),
        )
        self.finished_event.emit(event)
        self.finished.emit(payload)

    def emit_failed(
        self,
        exc: Exception | str,
        code: str | None = None,
        stop_reason: str = 'exception',
        *,
        metadata: Mapping[str, object] | None = None,
        severity: str | None = None,
    ) -> None:
        """Emit structured and legacy failure notifications.

        Args:
            exc: Exception instance or fallback failure message.
            code: Optional machine-readable error code override.
            stop_reason: Terminal stop reason.
            metadata: Optional structured metadata to project downstream.
            severity: Optional severity override for UI projection.
        """
        self._set_state(TaskState.FAILED.value)
        resolved_code = str(code or '')
        remediation_hint = ''
        error_metadata = dict(metadata or {})
        exception_type = exc.__class__.__name__ if isinstance(exc, Exception) else 'Exception'
        message = str(exc)
        resolved_severity = str(severity or 'error')
        if isinstance(exc, RobotSimError):
            resolved_code = str(code or exc.error_code)
            remediation_hint = str(exc.remediation_hint)
            error_metadata = {**dict(exc.metadata), **error_metadata}
            if isinstance(exc, CancelledTaskError):
                resolved_severity = 'info'
        event = WorkerFailedEvent(
            task_id=self.task_id,
            task_kind=self.task_kind,
            correlation_id=self.correlation_id,
            stop_reason=str(stop_reason),
            error_code=resolved_code,
            message=message,
            exception_type=exception_type,
            remediation_hint=remediation_hint,
            metadata=error_metadata,
            severity=resolved_severity,
            finished_at=datetime.now(timezone.utc),
        )
        self.failed_event.emit(event)
        self.failed.emit(message)

    def emit_cancelled(self, stop_reason: str = 'cancelled', *, message: str = 'cancelled', metadata: Mapping[str, object] | None = None) -> None:
        """Emit structured and legacy cancellation notifications.

        Args:
            stop_reason: Terminal cancellation reason such as ``cancelled`` or ``timeout``.
            message: User-facing cancellation message.
            metadata: Optional structured metadata for diagnostics.
        """
        self._set_state(TaskState.CANCELLED.value)
        event = WorkerCancelledEvent(
            task_id=self.task_id,
            task_kind=self.task_kind,
            correlation_id=self.correlation_id,
            stop_reason=str(stop_reason),
            message=str(message),
            metadata=dict(metadata or {}),
            finished_at=datetime.now(timezone.utc),
        )
        self.cancelled_event.emit(event)
        self.cancelled.emit()
