from __future__ import annotations

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view


class StatusCoordinator:
    """Project task snapshots and worker-failure state into the UI store."""

    def __init__(self, window, *, runtime=None) -> None:
        self.window = window
        self.runtime = require_dependency(runtime if runtime is not None else getattr(window, 'runtime_facade', None), 'runtime_facade')

    def apply_task_snapshot(self, snapshot) -> None:
        require_view(self.window, 'project_task_snapshot', snapshot)

    def handle_worker_failure(self, failure) -> None:
        mapper = self.runtime.task_error_mapper
        if hasattr(failure, 'error_code') or hasattr(failure, 'exception_type'):
            presentation = mapper.map_failed_event(failure)
        else:
            normalized = failure if isinstance(failure, Exception) else Exception(str(failure))
            presentation = mapper.map_exception(normalized)
        require_view(self.window, 'project_worker_failure', presentation)
