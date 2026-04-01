from __future__ import annotations
from typing import Callable, Protocol
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.domain.types import FloatArray

class InverseKinematicsSolver(Protocol):
    def solve(
        self,
        spec: RobotSpec,
        target: Pose,
        q0: FloatArray,
        config: IKConfig,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[IKIterationLog], None] | None = None,
    ) -> IKResult:
        ...
