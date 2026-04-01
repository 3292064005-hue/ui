import numpy as np

from robot_sim.model.trajectory import JointTrajectory


def test_trajectory_quality_properties_keep_canonical_names():
    traj = JointTrajectory(
        t=np.array([0.0, 1.0]),
        q=np.zeros((2, 1)),
        qd=np.zeros((2, 1)),
        qdd=np.zeros((2, 1)),
        quality={
            'goal_position_error': 0.1,
            'goal_orientation_error': 0.2,
            'start_to_end_position_delta': 0.3,
            'start_to_end_orientation_delta': 0.4,
        },
    )
    assert traj.goal_position_error == 0.1
    assert traj.goal_orientation_error == 0.2
    assert traj.start_to_end_position_delta == 0.3
    assert traj.start_to_end_orientation_delta == 0.4
