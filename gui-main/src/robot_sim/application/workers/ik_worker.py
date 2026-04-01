from __future__ import annotations
from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase

class IKWorker(BaseWorker):
    def __init__(self, request: IKRequest, use_case: RunIKUseCase) -> None:
        super().__init__(task_kind='ik')
        if use_case is None:
            raise ValueError('IKWorker requires an explicit IK use case')
        self._request = request
        self._use_case = use_case

    @Slot()
    def run(self) -> None:
        self.emit_started()
        try:
            result = self._use_case.execute(
                self._request,
                cancel_flag=self.is_cancel_requested,
                progress_cb=lambda payload: self.emit_progress(stage='ik', message='iterating', payload=payload if isinstance(payload, dict) else {'value': payload}),
            )
            if result.message == 'cancelled':
                self.emit_cancelled()
            else:
                self.emit_finished(result)
        except Exception as exc:
            self.emit_failed(exc)
