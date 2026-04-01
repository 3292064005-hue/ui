from __future__ import annotations

import numpy as np

from robot_sim.core.trajectory.quintic import QuinticTrajectoryPlanner
from robot_sim.core.trajectory.retiming import retime_trajectory


def test_retime_trajectory_scales_time_when_velocity_limit_is_tighter():
    traj = QuinticTrajectoryPlanner().plan(np.array([0.0]), np.array([2.0]), duration=1.0, dt=0.1)
    retimed = retime_trajectory(traj, max_velocity=0.2)

    assert retimed.t[-1] > traj.t[-1]
    assert retimed.metadata['retimed'] is True
    assert retimed.metadata['retime_scale'] > 1.0
    assert np.max(np.abs(retimed.qd)) < np.max(np.abs(traj.qd))
