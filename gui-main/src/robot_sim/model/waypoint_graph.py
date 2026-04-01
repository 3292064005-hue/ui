from __future__ import annotations

from dataclasses import dataclass, field
from robot_sim.model.pose import Pose


@dataclass(frozen=True)
class Waypoint:
    name: str
    pose: Pose
    duration_hint: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class WaypointGraph:
    waypoints: tuple[Waypoint, ...]
    metadata: dict[str, object] = field(default_factory=dict)
