from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskHandle:
    """Lightweight identity for an orchestrated background task.

    Attributes:
        task_id: Unique task identifier.
        task_kind: Logical task family.
        correlation_id: Optional correlation identifier for related task flows.
    """

    task_id: str
    task_kind: str
    correlation_id: str = ''
