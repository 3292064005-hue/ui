from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrajectoryQuality:
    max_velocity: float = 0.0
    max_acceleration: float = 0.0
    jerk_proxy: float = 0.0
    path_length: float = 0.0
    goal_position_error: float = 0.0
    goal_orientation_error: float = 0.0
    start_to_end_position_delta: float = 0.0
    start_to_end_orientation_delta: float = 0.0
    singularity_exposure: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            'max_velocity': self.max_velocity,
            'max_acceleration': self.max_acceleration,
            'jerk_proxy': self.jerk_proxy,
            'path_length': self.path_length,
            'goal_position_error': self.goal_position_error,
            'goal_orientation_error': self.goal_orientation_error,
            'start_to_end_position_delta': self.start_to_end_position_delta,
            'start_to_end_orientation_delta': self.start_to_end_orientation_delta,
            'singularity_exposure': self.singularity_exposure,
        }
