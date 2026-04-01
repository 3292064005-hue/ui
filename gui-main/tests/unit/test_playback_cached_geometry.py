from __future__ import annotations

import numpy as np

from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.model.trajectory import JointTrajectory


def test_playback_frame_uses_cached_geometry():
    traj = JointTrajectory(
        t=np.array([0.0, 0.1]),
        q=np.array([[0.0, 0.0], [0.2, 0.1]]),
        qd=np.zeros((2, 2)),
        qdd=np.zeros((2, 2)),
        ee_positions=np.array([[1.0, 0.0, 0.0], [0.98, 0.2, 0.0]]),
        joint_positions=np.array(
            [
                [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]],
                [[0.0, 0.0, 0.0], [0.49, 0.1, 0.0], [0.98, 0.2, 0.0]],
            ]
        ),
    )
    frame = PlaybackService().frame(traj, 1)
    assert frame.ee_position is not None
    assert frame.joint_positions is not None
    assert np.allclose(frame.ee_position, [0.98, 0.2, 0.0])
    assert np.allclose(frame.joint_positions[-1], frame.ee_position)
