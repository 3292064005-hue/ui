from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CollisionResult:
    self_collision: bool = False
    environment_collision: bool = False
    self_pairs: tuple[tuple[str, str], ...] = ()
    environment_pairs: tuple[tuple[str, str], ...] = ()
    ignored_pairs: tuple[tuple[str, str], ...] = ()
    checked_pairs: tuple[tuple[str, str], ...] = ()
    scene_revision: int = 0
    collision_level: str = 'aabb'
    clearance_metric: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)
