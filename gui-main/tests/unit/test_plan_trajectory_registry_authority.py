import numpy as np
import pytest

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.core.trajectory.registry import TrajectoryPlannerRegistry
from robot_sim.domain.enums import JointType
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_spec import RobotSpec


def _spec() -> RobotSpec:
    return RobotSpec(
        name='r',
        dh_rows=(DHRow(0, 0, 0, 0, JointType.REVOLUTE, -3.14, 3.14),),
        base_T=np.eye(4),
        tool_T=np.eye(4),
        home_q=np.zeros(1),
    )


def test_plan_trajectory_use_case_uses_only_injected_registry():
    uc = PlanTrajectoryUseCase(TrajectoryPlannerRegistry())
    req = TrajectoryRequest(spec=_spec(), q_start=np.zeros(1), q_goal=np.ones(1), duration=1.0, dt=0.1)
    with pytest.raises(KeyError):
        uc.execute(req)
