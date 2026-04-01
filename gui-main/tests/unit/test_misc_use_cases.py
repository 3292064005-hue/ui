from __future__ import annotations

import numpy as np

from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.capture_scene import CaptureSceneUseCase
from robot_sim.application.use_cases.load_robot import LoadRobotUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.model.trajectory import JointTrajectory


class _Registry:
    def __init__(self):
        self.loaded = []

    def load(self, name: str):
        self.loaded.append(name)
        return {'name': name}


class _ScreenshotService:
    def __init__(self):
        self.calls = []

    def capture(self, widget, path):
        self.calls.append((widget, path))
        return path


def _trajectory() -> JointTrajectory:
    t = np.array([0.0, 0.5, 1.0], dtype=float)
    q = np.array([[0.0, 0.0], [0.5, 0.25], [1.0, 0.5]], dtype=float)
    zeros = np.zeros_like(q)
    ee = np.array([[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.4, 0.0, 0.0]], dtype=float)
    return JointTrajectory(t=t, q=q, qd=zeros, qdd=zeros, ee_positions=ee)


def test_capture_scene_use_case_delegates():
    service = _ScreenshotService()
    uc = CaptureSceneUseCase(service)
    widget = object()
    path = 'scene.png'
    assert uc.execute(widget, path) == path
    assert service.calls == [(widget, path)]


def test_load_robot_use_case_delegates():
    registry = _Registry()
    uc = LoadRobotUseCase(registry)
    assert uc.execute('planar') == {'name': 'planar'}
    assert registry.loaded == ['planar']


def test_step_playback_use_case_covers_current_next_previous():
    traj = _trajectory()
    service = PlaybackService()
    uc = StepPlaybackUseCase(service)
    state = service.build_state(traj, frame_idx=0, loop_enabled=True)

    current = uc.current(traj, state)
    assert current.frame_idx == 0

    next_state, next_frame = uc.next(traj, state)
    assert next_state.frame_idx == 1
    assert next_frame is not None and next_frame.frame_idx == 1

    prev_state, prev_frame = uc.previous(traj, next_state)
    assert prev_state.frame_idx == 0
    assert prev_frame is not None and prev_frame.frame_idx == 0

    stopped_state, no_frame = uc.next(traj, service.build_state(traj, frame_idx=2, loop_enabled=False))
    assert no_frame is None
    assert stopped_state.is_playing is False
