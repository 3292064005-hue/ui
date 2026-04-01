from __future__ import annotations

import numpy as np

from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.ik_result import IKResult
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.state_store import StateStore


def test_trajectory_controller_builds_joint_request(project_root):
    cfg = ConfigService(project_root / 'configs')
    state = StateStore(SessionState())
    fk_uc = RunFKUseCase()
    spec = None
    from robot_sim.application.services.robot_registry import RobotRegistry
    spec = RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')
    fk = fk_uc.execute(type('FKReq', (), {'spec': spec, 'q': spec.home_q.copy()})())
    state.patch(robot_spec=spec, q_current=spec.home_q.copy(), fk_result=fk, ik_result=IKResult(True, np.array([0.1, -0.1]), tuple(), 'ok'))
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    traj_uc = PlanTrajectoryUseCase(build_default_planner_registry(ik_uc))
    ik_ctrl = IKController(state, cfg.load_solver_config()['ik'], fk_uc, ik_uc)
    traj_ctrl = TrajectoryController(state, traj_uc, PlaybackService(), ik_ctrl.build_ik_request)
    req = traj_ctrl.build_trajectory_request(duration=1.0, dt=0.1)
    assert req.q_goal is not None
    assert req.mode.value == 'joint_space'
