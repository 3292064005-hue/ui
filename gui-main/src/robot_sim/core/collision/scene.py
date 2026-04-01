from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import AABB
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import CollisionLevel

_COLLISION_BACKEND_REGISTRY = default_collision_backend_registry()
_COLLISION_BACKEND_FALLBACK = _COLLISION_BACKEND_REGISTRY.default_backend


def _normalize_collision_backend(backend_id: str, metadata: dict[str, object] | None = None) -> tuple[str, dict[str, object]]:
    """Normalize a requested collision backend against the canonical registry."""
    return _COLLISION_BACKEND_REGISTRY.normalize_backend(str(backend_id), metadata=metadata)


@dataclass(frozen=True)
class SceneObject:
    object_id: str
    geometry: AABB
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanningScene:
    obstacles: tuple[SceneObject, ...] = ()
    allowed_collision_matrix: AllowedCollisionMatrix = field(default_factory=AllowedCollisionMatrix)
    revision: int = 0
    collision_level: CollisionLevel = CollisionLevel.AABB
    self_collision_padding: float = 0.03
    environment_collision_padding: float = 0.02
    ignore_adjacent_self_collisions: bool = True
    geometry_source: str = 'generated'
    collision_backend: str = _COLLISION_BACKEND_FALLBACK
    attached_objects: tuple[SceneObject, ...] = ()
    clearance_policy: str = 'min_distance'
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def obstacle_ids(self) -> tuple[str, ...]:
        return tuple(obj.object_id for obj in self.obstacles)

    def add_obstacle(self, object_id: str, geometry: AABB, *, metadata: dict[str, object] | None = None) -> 'PlanningScene':
        return PlanningScene(
            obstacles=self.obstacles + (SceneObject(object_id=object_id, geometry=geometry, metadata=dict(metadata or {})),),
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def remove_obstacle(self, object_id: str) -> 'PlanningScene':
        remaining = tuple(obj for obj in self.obstacles if obj.object_id != str(object_id))
        if remaining == self.obstacles:
            return self
        return PlanningScene(
            obstacles=remaining,
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def clear_obstacles(self) -> 'PlanningScene':
        if not self.obstacles:
            return self
        return PlanningScene(
            obstacles=(),
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def with_acm(self, allowed_collision_matrix: AllowedCollisionMatrix) -> 'PlanningScene':
        return PlanningScene(
            obstacles=self.obstacles,
            allowed_collision_matrix=allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def with_revision_bump(self) -> 'PlanningScene':
        return PlanningScene(
            obstacles=self.obstacles,
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def with_collision_backend(self, backend_id: str) -> 'PlanningScene':
        resolved_backend, metadata = _normalize_collision_backend(str(backend_id), metadata=self.metadata)
        return PlanningScene(
            obstacles=self.obstacles,
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=resolved_backend,
            attached_objects=self.attached_objects,
            clearance_policy=self.clearance_policy,
            metadata=metadata,
        )

    def attach_object(self, object_id: str, geometry: AABB, *, metadata: dict[str, object] | None = None) -> 'PlanningScene':
        return PlanningScene(
            obstacles=self.obstacles,
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=self.attached_objects + (SceneObject(object_id=object_id, geometry=geometry, metadata=dict(metadata or {})),),
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def detach_object(self, object_id: str) -> 'PlanningScene':
        remaining = tuple(obj for obj in self.attached_objects if obj.object_id != str(object_id))
        if remaining == self.attached_objects:
            return self
        return PlanningScene(
            obstacles=self.obstacles,
            allowed_collision_matrix=self.allowed_collision_matrix,
            revision=self.revision + 1,
            collision_level=self.collision_level,
            self_collision_padding=self.self_collision_padding,
            environment_collision_padding=self.environment_collision_padding,
            ignore_adjacent_self_collisions=self.ignore_adjacent_self_collisions,
            geometry_source=self.geometry_source,
            collision_backend=self.collision_backend,
            attached_objects=remaining,
            clearance_policy=self.clearance_policy,
            metadata=dict(self.metadata),
        )

    def summary(self) -> dict[str, object]:
        return {
            'revision': int(self.revision),
            'collision_backend': str(self.collision_backend),
            'requested_collision_backend': str(self.metadata.get('requested_collision_backend', self.collision_backend)),
            'obstacle_ids': list(self.obstacle_ids),
            'attached_object_ids': [obj.object_id for obj in self.attached_objects],
            'collision_level': getattr(self.collision_level, 'value', str(self.collision_level)),
            'self_collision_padding': float(self.self_collision_padding),
            'environment_collision_padding': float(self.environment_collision_padding),
        }
