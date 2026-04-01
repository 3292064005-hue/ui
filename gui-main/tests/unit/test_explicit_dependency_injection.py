import pytest

from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.presentation.controllers.diagnostics_controller import DiagnosticsController
from robot_sim.application.workers.playback_worker import PlaybackWorker
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory
import numpy as np
from robot_sim.presentation.state_store import StateStore
from robot_sim.model.session_state import SessionState


def test_step_playback_use_case_requires_explicit_service():
    with pytest.raises(ValueError):
        StepPlaybackUseCase(None)  # type: ignore[arg-type]


def test_diagnostics_controller_requires_explicit_metrics_service():
    with pytest.raises(ValueError):
        DiagnosticsController(StateStore(SessionState()), None)  # type: ignore[arg-type]


def test_playback_worker_requires_explicit_playback_service():
    traj = JointTrajectory(t=np.array([0.0]), q=np.array([[0.0]]), qd=np.array([[0.0]]), qdd=np.array([[0.0]]))
    with pytest.raises(ValueError):
        PlaybackWorker(traj, PlaybackState(total_frames=1), None)  # type: ignore[arg-type]
