import numpy as np

from robot_sim.model.trajectory import JointTrajectory


def test_trajectory_feasibility_projection_reads_typed_fields():
    traj = JointTrajectory(t=np.array([0.0, 1.0]), q=np.zeros((2,1)), qd=np.zeros((2,1)), qdd=np.zeros((2,1)), feasibility={'feasible': False, 'reasons': ['collision']})
    assert traj.typed_feasibility.feasible is False
    assert traj.typed_feasibility.reasons == ('collision',)
