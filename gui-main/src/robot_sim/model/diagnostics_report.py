from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrajectoryDiagnosticsReport:
    feasible: bool
    reasons: tuple[str, ...] = ()
    max_velocity: float = 0.0
    max_acceleration: float = 0.0
    jerk_proxy: float = 0.0
    goal_position_error: float = 0.0
    goal_orientation_error: float = 0.0
    start_to_end_position_delta: float = 0.0
    start_to_end_orientation_delta: float = 0.0
    path_length: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def endpoint_position_error(self) -> float:
        return self.goal_position_error

    @property
    def endpoint_orientation_error(self) -> float:
        return self.goal_orientation_error
