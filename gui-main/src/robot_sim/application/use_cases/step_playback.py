from __future__ import annotations

from robot_sim.application.services.playback_service import PlaybackService, PlaybackFrame
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory


class StepPlaybackUseCase:
    def __init__(self, service: PlaybackService) -> None:
        if service is None:
            raise ValueError('StepPlaybackUseCase requires an explicit playback service')
        self._service = service

    def current(self, trajectory: JointTrajectory, state: PlaybackState) -> PlaybackFrame:
        return self._service.frame(trajectory, state.frame_idx)

    def next(self, trajectory: JointTrajectory, state: PlaybackState) -> tuple[PlaybackState, PlaybackFrame | None]:
        next_idx = self._service.next_index(state)
        if next_idx is None:
            return state.stop(), None
        new_state = state.with_frame(next_idx)
        return new_state, self._service.frame(trajectory, next_idx)

    def previous(self, trajectory: JointTrajectory, state: PlaybackState) -> tuple[PlaybackState, PlaybackFrame | None]:
        prev_idx = self._service.previous_index(state)
        if prev_idx is None:
            return state, None
        new_state = state.with_frame(prev_idx)
        return new_state, self._service.frame(trajectory, prev_idx)
