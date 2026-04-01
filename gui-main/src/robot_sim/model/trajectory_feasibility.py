from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrajectoryFeasibility:
    feasible: bool = True
    reasons: tuple[str, ...] = ()
    collision_summary: dict[str, object] = field(default_factory=dict)
    limit_summary: dict[str, object] = field(default_factory=dict)
    timing_summary: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            'feasible': self.feasible,
            'reasons': list(self.reasons),
            'collision_summary': dict(self.collision_summary),
            'limit_summary': dict(self.limit_summary),
            'timing_summary': dict(self.timing_summary),
        }
