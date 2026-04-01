from __future__ import annotations

from robot_sim.domain.error_projection import TaskErrorMapper as DomainTaskErrorMapper


class TaskErrorMapper(DomainTaskErrorMapper):
    """Application-layer compatibility wrapper over the canonical task-error mapper.

    The canonical implementation now lives in ``robot_sim.domain.error_projection`` so that
    both direct exception projection and worker failure-event projection share a single source
    of truth. This wrapper preserves the previous import path used by the composition root.
    """


__all__ = ['TaskErrorMapper']
