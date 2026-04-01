from __future__ import annotations
from robot_sim.application.dto import FKRequest
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver

class RunFKUseCase:
    def __init__(self) -> None:
        self._solver = ForwardKinematicsSolver()

    def execute(self, req: FKRequest):
        return self._solver.solve(req.spec, req.q)
