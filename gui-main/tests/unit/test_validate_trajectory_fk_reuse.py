from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.plan_joint_trajectory import PlanJointTrajectoryUseCase
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase


def test_validate_trajectory_reuses_terminal_cached_fk_for_goal_pose(planar_spec, monkeypatch):
    req = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.4, -0.1]),
        duration=1.0,
        dt=0.2,
        spec=planar_spec,
    )
    traj = PlanJointTrajectoryUseCase().execute(req)
    validate_uc = ValidateTrajectoryUseCase()

    def _unexpected_fk(*args, **kwargs):
        raise AssertionError('goal FK should not be recomputed when terminal cached FK is complete')

    monkeypatch.setattr(validate_uc._fk, 'solve', _unexpected_fk)
    report = validate_uc.execute(traj, spec=planar_spec, q_goal=req.q_goal)

    assert report.metadata['goal_pose_source'] == 'cached_terminal_fk'
    assert report.metadata['cache_used'] is True
