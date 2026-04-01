from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.threading.task_handle import TaskHandle


class TaskLifecycleRegistry:
    """Maintain active task identity and emitted lifecycle snapshots."""

    def __init__(self, emitter: Callable[[TaskSnapshot], None]) -> None:
        """Initialize lifecycle tracking state.

        Args:
            emitter: Snapshot emitter invoked whenever lifecycle state changes.

        Returns:
            None: Initializes runtime and terminal tracking state.

        Raises:
            None: Construction is side-effect free.
        """
        self._emitter = emitter
        self.reset_runtime()
        self._last_terminal_snapshot: TaskSnapshot | None = None

    def reset_runtime(self) -> None:
        """Reset transient runtime state for the active task.

        Returns:
            None: Clears active-task state while preserving terminal history.

        Raises:
            None: Pure in-memory reset.
        """
        self.active_task: TaskHandle | None = None
        self.active_state: TaskState = TaskState.IDLE
        self.last_snapshot: TaskSnapshot | None = None
        self.terminal_lock_task_id: str | None = None

    def current_task_id(self) -> str:
        """Return the active task identifier or an empty string."""
        return self.active_task.task_id if self.active_task is not None else ''

    def mark_terminal_locked(self, task_id: str) -> None:
        """Prevent later worker events from overwriting a terminal snapshot."""
        if task_id:
            self.terminal_lock_task_id = str(task_id)

    def is_terminal_locked(self) -> bool:
        """Return whether the current task terminal state is already committed."""
        task_id = self.current_task_id()
        return bool(task_id and self.terminal_lock_task_id == task_id and self._last_terminal_snapshot is not None)

    @property
    def last_terminal_snapshot(self) -> TaskSnapshot | None:
        """Return the most recent terminal snapshot."""
        return self._last_terminal_snapshot

    def begin(self, task: TaskHandle) -> None:
        """Begin tracking a new active task."""
        self.active_task = TaskHandle(task.task_id, task.task_kind, task.correlation_id or task.task_id)
        self.active_state = TaskState.IDLE
        self.last_snapshot = None
        self.terminal_lock_task_id = None

    def set_state(
        self,
        state: TaskState,
        *,
        stage: str = '',
        percent: float = 0.0,
        message: str = '',
        stop_reason: str = '',
        finished: bool = False,
        finished_at: datetime | None = None,
    ) -> TaskSnapshot | None:
        """Build and emit a structured task snapshot for the active task."""
        self.active_state = state
        if self.active_task is None:
            return None
        now = datetime.now(timezone.utc)
        previous_snapshot = self.last_snapshot
        started_at = now
        if previous_snapshot is not None and previous_snapshot.task_id == self.active_task.task_id and previous_snapshot.started_at is not None:
            started_at = previous_snapshot.started_at
        snapshot = TaskSnapshot(
            task_id=self.active_task.task_id,
            task_kind=self.active_task.task_kind,
            task_state=state,
            progress_stage=stage,
            progress_percent=percent,
            message=message,
            correlation_id=self.active_task.correlation_id,
            started_at=started_at,
            finished_at=finished_at or (now if finished else None),
            stop_reason=stop_reason,
        )
        self.last_snapshot = snapshot
        if finished:
            self._last_terminal_snapshot = snapshot
            self.mark_terminal_locked(self.active_task.task_id)
        self._emitter(snapshot)
        return snapshot
