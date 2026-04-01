from __future__ import annotations

import time

from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory


class PlaybackWorker(BaseWorker):
    def __init__(self, trajectory: JointTrajectory, state: PlaybackState, service: PlaybackService, frame_interval_ms: int = 30) -> None:
        super().__init__(task_kind='playback')
        if service is None:
            raise ValueError('PlaybackWorker requires an explicit playback service')
        self._trajectory = trajectory
        self._playback_state = state
        self._frame_interval_ms = max(int(frame_interval_ms), 5)
        self._service = service

    @Slot()
    def run(self) -> None:
        self.emit_started()
        try:
            state = self._playback_state.play()
            if state.total_frames <= 0:
                self.emit_failed('trajectory has no frames')
                return
            while not self.is_cancel_requested():
                frame = self._service.frame(self._trajectory, state.frame_idx)
                self.progress.emit(frame)
                next_idx = self._service.next_index(state)
                if next_idx is None:
                    self.emit_finished(state.stop())
                    return
                sleep_s = self._compute_sleep_seconds(state.frame_idx, next_idx, state.speed_multiplier)
                state = state.with_frame(next_idx)
                if self._sleep_interruptibly(sleep_s):
                    self.emit_cancelled()
                    return
            self.emit_cancelled()
        except Exception as exc:
            self.emit_failed(exc)

    def _compute_sleep_seconds(self, current_idx: int, next_idx: int, speed_multiplier: float) -> float:
        if self._trajectory.t.shape[0] >= 2:
            dt = float(self._trajectory.t[next_idx] - self._trajectory.t[current_idx])
            if dt > 0.0:
                return max(dt / max(speed_multiplier, 0.05), 0.001)
        return self._frame_interval_ms / 1000.0 / max(speed_multiplier, 0.05)

    def _sleep_interruptibly(self, sleep_s: float) -> bool:
        deadline = time.perf_counter() + max(float(sleep_s), 0.0)
        while time.perf_counter() < deadline:
            if self.is_cancel_requested():
                return True
            remaining = deadline - time.perf_counter()
            time.sleep(min(remaining, 0.01))
        return self.is_cancel_requested()
