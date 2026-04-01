from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.domain.enums import TrajectoryMode
from robot_sim.model.solver_config import IKConfig


def test_plan_cartesian_trajectory_position_only(planar_spec):
    fk_solver = ForwardKinematicsSolver()
    q_goal = np.array([0.6, -0.35])
    target_pose = fk_solver.solve(planar_spec, q_goal).ee_pose
    req = TrajectoryRequest(
        q_start=planar_spec.home_q.copy(),
        q_goal=None,
        duration=1.0,
        dt=0.1,
        spec=planar_spec,
        mode=TrajectoryMode.CARTESIAN,
        target_pose=target_pose,
        ik_config=IKConfig(position_only=True, retry_count=1),
    )
    traj = PlanTrajectoryUseCase(build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry()))).execute(req)
    assert traj.metadata['mode'] == 'cartesian_pose'
    assert traj.ee_positions is not None
    assert traj.ee_rotations is not None
    assert traj.joint_positions is not None
    assert np.linalg.norm(traj.ee_positions[-1] - target_pose.p) < 1e-2
