from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry


def test_plan_trajectory_populates_quality_and_feasibility(planar_spec):
    req = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.2, -0.1]),
        duration=1.0,
        dt=0.1,
        spec=planar_spec,
    )
    traj = PlanTrajectoryUseCase(build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry()))).execute(req)
    assert 'jerk_proxy' in traj.quality
    assert 'feasible' in traj.feasibility
    assert traj.metadata['export_version'] == 'v7'
