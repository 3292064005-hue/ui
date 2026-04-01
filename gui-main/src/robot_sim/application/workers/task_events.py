from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC timestamp for worker task events."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkerProgressEvent:
    """Structured progress payload emitted by background workers.

    Attributes:
        task_id: Stable task identifier assigned by the worker or orchestrator.
        task_kind: Human-readable task category such as ``ik`` or ``trajectory``.
        stage: Fine-grained execution stage for status projection.
        percent: Progress percentage in the ``[0, 100]`` range.
        message: User-facing status message.
        correlation_id: Correlation identifier propagated across worker layers.
        payload: Auxiliary structured payload for logging or GUI projection.
        emitted_at: UTC timestamp when the event was created.
    """

    task_id: str = ''
    task_kind: str = ''
    stage: str = ''
    percent: float = 0.0
    message: str = ''
    correlation_id: str = ''
    payload: dict[str, object] = field(default_factory=dict)
    emitted_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class WorkerFinishedEvent:
    """Structured terminal success payload emitted by background workers."""

    task_id: str = ''
    task_kind: str = ''
    correlation_id: str = ''
    stop_reason: str = 'completed'
    payload: object = None
    metadata: dict[str, object] = field(default_factory=dict)
    finished_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class WorkerFailedEvent:
    """Structured terminal failure payload emitted by background workers."""

    task_id: str = ''
    task_kind: str = ''
    correlation_id: str = ''
    stop_reason: str = 'exception'
    error_code: str = ''
    message: str = ''
    exception_type: str = ''
    remediation_hint: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    severity: str = 'error'
    finished_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class WorkerCancelledEvent:
    """Structured terminal cancellation payload emitted by background workers."""

    task_id: str = ''
    task_kind: str = ''
    correlation_id: str = ''
    stop_reason: str = 'cancelled'
    message: str = 'cancelled'
    metadata: dict[str, object] = field(default_factory=dict)
    finished_at: datetime = field(default_factory=utc_now)
