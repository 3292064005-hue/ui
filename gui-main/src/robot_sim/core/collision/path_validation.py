from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PathValidationSummary:
    collision: bool = False
    checked_samples: int = 0
    min_clearance: float = 0.0


def sample_segment_count(num_waypoints: int, samples_per_segment: int = 10) -> int:
    if num_waypoints <= 1:
        return 0
    return int((num_waypoints - 1) * max(samples_per_segment, 1))
