from __future__ import annotations

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.state_store import StateStore


def test_robot_controller_loads_robot(project_root):
    state = StateStore(SessionState())
    registry = RobotRegistry(project_root / 'configs' / 'robots')
    controller = RobotController(state, registry, RunFKUseCase())
    fk = controller.load_robot('planar_2dof')
    assert state.state.robot_spec is not None
    assert fk.ee_pose.p.shape == (3,)
