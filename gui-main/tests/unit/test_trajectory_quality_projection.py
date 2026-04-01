import numpy as np

from robot_sim.model.trajectory import JointTrajectory


def test_trajectory_quality_projection_reads_typed_fields():
    traj = JointTrajectory(t=np.array([0.0, 1.0]), q=np.zeros((2,1)), qd=np.zeros((2,1)), qdd=np.zeros((2,1)), quality={'goal_position_error': 0.1})
    assert traj.typed_quality.goal_position_error == 0.1
