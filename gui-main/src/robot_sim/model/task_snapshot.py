from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from robot_sim.domain.enums import TaskState


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    task_kind: str
    task_state: TaskState
    progress_stage: str = ''
    progress_percent: float = 0.0
    message: str = ''
    correlation_id: str = ''
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stop_reason: str = ''

    @property
    def state(self) -> str:
        return self.task_state.value
