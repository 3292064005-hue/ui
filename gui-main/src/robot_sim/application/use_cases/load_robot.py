from __future__ import annotations
from robot_sim.application.services.robot_registry import RobotRegistry

class LoadRobotUseCase:
    def __init__(self, registry: RobotRegistry) -> None:
        self._registry = registry

    def execute(self, name: str):
        return self._registry.load(name)
