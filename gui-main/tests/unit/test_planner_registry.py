from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.core.trajectory.retiming import suggest_duration


def test_retiming_suggests_positive_duration():
    duration = suggest_duration([0.0, 0.0], [1.0, -0.5], max_velocity=0.5, max_acceleration=1.0)
    assert duration > 1.0


def test_plan_trajectory_supports_trapezoidal_plugin(planar_spec):
    reg = build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry()))
    uc = PlanTrajectoryUseCase(reg)
    req = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.3, -0.2]),
        duration=1.0,
        dt=0.1,
        spec=planar_spec,
        planner_id='joint_trapezoidal',
    )
    traj = uc.execute(req)
    assert traj.metadata['planner_id'] == 'joint_trapezoidal'
    assert traj.metadata['planner_type'] == 'joint_trapezoidal'
    assert traj.metadata['planner_family'] == 'joint'
    assert traj.q.shape[0] > 2
