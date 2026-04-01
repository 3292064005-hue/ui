from __future__ import annotations
from robot_sim.application.services.export_service import ExportService
from robot_sim.model.session_state import SessionState


class SaveSessionUseCase:
    def __init__(self, exporter: ExportService) -> None:
        self._exporter = exporter

    def execute(self, name: str, state: SessionState):
        return self._exporter.save_session(name, state)
