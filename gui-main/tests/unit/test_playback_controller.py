from __future__ import annotations

import numpy as np

from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.presentation.controllers.playback_controller import PlaybackController
from robot_sim.presentation.state_store import StateStore


def test_playback_controller_updates_frame_index():
    traj = JointTrajectory(
        t=np.array([0.0, 0.1, 0.2]),
        q=np.zeros((3, 1)),
        qd=np.zeros((3, 1)),
        qdd=np.zeros((3, 1)),
        ee_positions=np.zeros((3, 3)),
        joint_positions=np.zeros((3, 2, 3)),
        ee_rotations=np.repeat(np.eye(3)[None, :, :], 3, axis=0),
    )
    state = StateStore(SessionState(trajectory=traj, playback=PlaybackState(total_frames=3)))
    controller = PlaybackController(state, PlaybackService(), StepPlaybackUseCase(PlaybackService()))
    frame = controller.set_playback_frame(2)
    assert frame.frame_idx == 2
    controller.set_playback_options(speed_multiplier=2.0)
    assert state.state.playback.speed_multiplier == 2.0
