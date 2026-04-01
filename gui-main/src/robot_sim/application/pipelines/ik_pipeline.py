from __future__ import annotations

from robot_sim.application.dto import IKRequest
from robot_sim.model.ik_result import IKResult


class IKExecutionPipeline:
    """Lightweight authority pipeline around RunIKUseCase.

    V7 keeps the heavy lifting inside the use case and solver registry, but the
    pipeline gives the orchestration layer a named contract for future adapters,
    prechecks, and post-validation without pushing more logic into the window.
    """

    def __init__(self, run_ik_uc) -> None:
        self._run_ik_uc = run_ik_uc

    def execute(self, req: IKRequest, *, cancel_flag=None, progress_cb=None) -> IKResult:
        return self._run_ik_uc.execute(req, cancel_flag=cancel_flag, progress_cb=progress_cb)
