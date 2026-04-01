from __future__ import annotations
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.dto import FKRequest
from robot_sim.application.use_cases.run_fk import RunFKUseCase

class FKWorker(BaseWorker):
    def __init__(self, request: FKRequest, use_case: RunFKUseCase) -> None:
        super().__init__(task_kind='fk')
        if use_case is None:
            raise ValueError('FKWorker requires an explicit FK use case')
        self._request = request
        self._use_case = use_case

    @Slot()
    def run(self) -> None:
        self.emit_started()
        try:
            result = self._use_case.execute(self._request)
            self.emit_finished(result)
        except Exception as exc:
            self.emit_failed(exc)
