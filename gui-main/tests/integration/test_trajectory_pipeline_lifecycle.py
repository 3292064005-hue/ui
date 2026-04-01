from __future__ import annotations

import numpy as np

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.application.dto import TrajectoryRequest


def test_trajectory_pipeline_runs_joint_quintic_end_to_end():
    container = build_container(get_project_root())
    spec = container.robot_registry.load('planar_2dof')
    traj = container.traj_uc.execute(
        TrajectoryRequest(
            q_start=np.asarray(spec.home_q, dtype=float),
            q_goal=np.array([0.2, -0.15], dtype=float),
            duration=1.0,
            dt=0.05,
            spec=spec,
            max_velocity=2.0,
            max_acceleration=4.0,
        )
    )
    assert traj.q.shape[0] > 2
    assert traj.metadata['planner_id'] == 'joint_quintic'
    assert traj.metadata['export_version'] == 'v7'
