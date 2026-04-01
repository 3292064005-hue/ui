from __future__ import annotations

from robot_sim.application.services.playback_service import PlaybackFrame, PlaybackService
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.model.playback_state import PlaybackState
from robot_sim.presentation.state_store import StateStore


class PlaybackController:
    """Presentation controller for trajectory playback."""

    def __init__(self, state_store: StateStore, playback_service: PlaybackService, playback_uc: StepPlaybackUseCase) -> None:
        self._state_store = state_store
        self._playback_service = playback_service
        self._playback_uc = playback_uc

    def ensure_playback_ready(self, *, strict: bool = True) -> None:
        """Validate the active trajectory against the playback cache contract."""
        trajectory = self._trajectory_or_raise(strict=strict)
        self._playback_service.ensure_playback_ready(trajectory, strict=strict)

    def _trajectory_or_raise(self, *, strict: bool = True):
        trajectory = self._state_store.state.trajectory
        if trajectory is None:
            raise RuntimeError('trajectory not available')
        if strict:
            self._playback_service.ensure_playback_ready(trajectory, strict=True)
        elif not trajectory.has_cached_joint_positions and trajectory.cache_status in {'ready', 'partial', 'recomputed'}:
            raise RuntimeError('trajectory cache is inconsistent: missing joint_positions')
        return trajectory

    def current_playback_frame(self) -> PlaybackFrame:
        trajectory = self._trajectory_or_raise(strict=True)
        return self._playback_uc.current(trajectory, self._state_store.state.playback)

    def set_playback_frame(self, frame_idx: int) -> PlaybackFrame:
        trajectory = self._trajectory_or_raise(strict=True)
        state = self._state_store.state.playback.with_frame(frame_idx)
        frame = self._playback_service.frame(trajectory, state.frame_idx)
        self._state_store.patch(playback=state)
        return frame

    def next_playback_frame(self) -> PlaybackFrame | None:
        trajectory = self._trajectory_or_raise(strict=True)
        state, frame = self._playback_uc.next(trajectory, self._state_store.state.playback)
        self._state_store.patch(playback=state)
        return frame

    def set_playback_options(self, *, speed_multiplier: float | None = None, loop_enabled: bool | None = None) -> None:
        playback = self._state_store.state.playback
        if speed_multiplier is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=max(float(speed_multiplier), 0.05),
                loop_enabled=playback.loop_enabled if loop_enabled is None else bool(loop_enabled),
            )
        elif loop_enabled is not None:
            playback = PlaybackState(
                is_playing=playback.is_playing,
                frame_idx=playback.frame_idx,
                total_frames=playback.total_frames,
                speed_multiplier=playback.speed_multiplier,
                loop_enabled=bool(loop_enabled),
            )
        self._state_store.patch(playback=playback)
