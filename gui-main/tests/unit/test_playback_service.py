from __future__ import annotations

import numpy as np

from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory


def make_traj() -> JointTrajectory:
    t = np.array([0.0, 0.1, 0.2])
    q = np.array([[0.0, 0.0], [0.2, 0.1], [0.5, 0.3]])
    qd = np.zeros_like(q)
    qdd = np.zeros_like(q)
    return JointTrajectory(t=t, q=q, qd=qd, qdd=qdd)


def test_playback_service_frame_and_loop():
    service = PlaybackService()
    traj = make_traj()
    state = service.build_state(traj, frame_idx=0, speed_multiplier=1.5, loop_enabled=True)
    frame0 = service.frame(traj, state.frame_idx)
    assert frame0.frame_idx == 0
    assert np.allclose(frame0.q, traj.q[0])
    assert service.next_index(state.with_frame(2)) == 0
    assert service.previous_index(state.with_frame(0)) == 2


def test_step_playback_use_case_advances_and_stops_without_loop():
    uc = StepPlaybackUseCase(PlaybackService())
    traj = make_traj()
    state = PlaybackState(frame_idx=1, total_frames=3, loop_enabled=False)
    state2, frame2 = uc.next(traj, state)
    assert frame2 is not None
    assert frame2.frame_idx == 2
    final_state, maybe_none = uc.next(traj, state2)
    assert maybe_none is None
    assert final_state.is_playing is False
