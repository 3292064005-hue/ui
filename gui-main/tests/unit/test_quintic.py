from __future__ import annotations
import numpy as np
from robot_sim.core.trajectory.quintic import QuinticTrajectoryPlanner

def test_quintic_boundary_conditions():
    planner = QuinticTrajectoryPlanner()
    traj = planner.plan(np.array([0.0, 1.0]), np.array([1.0, 2.0]), duration=2.0, dt=0.01)
    assert np.allclose(traj.q[0], [0.0, 1.0], atol=1e-8)
    assert np.allclose(traj.q[-1], [1.0, 2.0], atol=1e-8)
    assert np.allclose(traj.qd[0], [0.0, 0.0], atol=1e-6)
    assert np.allclose(traj.qd[-1], [0.0, 0.0], atol=1e-4)
