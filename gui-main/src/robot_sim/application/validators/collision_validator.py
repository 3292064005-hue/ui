from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json

import numpy as np

from robot_sim.core.collision.aabb import broad_phase_intersections
from robot_sim.core.collision.collision_result import CollisionResult
from robot_sim.core.collision.environment_collision import environment_collision_flags
from robot_sim.core.collision.geometry import AABB, aabb_from_points
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.model.trajectory_digest import ensure_trajectory_digest_metadata


class _BoundedLruCache:
    """Small process-local LRU cache used by collision validation helpers."""

    def __init__(self, max_entries: int = 16) -> None:
        self._max_entries = max(1, int(max_entries))
        self._entries: dict[tuple[object, ...], object] = {}

    def get(self, key: tuple[object, ...]) -> object | None:
        """Return a cached value for the supplied key."""
        cached = self._entries.get(key)
        if cached is None:
            return None
        self._entries.pop(key, None)
        self._entries[key] = cached
        return cached

    def put(self, key: tuple[object, ...], value: object) -> None:
        """Store a value while keeping the cache bounded."""
        self._entries.pop(key, None)
        self._entries[key] = value
        while len(self._entries) > self._max_entries:
            oldest = next(iter(self._entries))
            self._entries.pop(oldest, None)


@dataclass(frozen=True)
class _SceneFrameGeometry:
    """Precomputed per-frame link AABBs and self-collision hits for one trajectory."""

    frame_boxes: tuple[tuple[AABB, ...], ...]
    self_hits: tuple[frozenset[tuple[str, str]], ...]


@dataclass(frozen=True)
class _LegacyFrameGeometry:
    """Precomputed per-frame robot AABBs for legacy obstacle checks."""

    robot_boxes: tuple[AABB, ...]


_COLLISION_CACHE = _BoundedLruCache(max_entries=16)
_GEOMETRY_CACHE = _BoundedLruCache(max_entries=24)
_COLLISION_BACKEND_REGISTRY = default_collision_backend_registry()


def evaluate_collision_summary(trajectory, *, planning_scene=None, collision_obstacles=()) -> tuple[list[str], dict[str, object]]:
    """Evaluate collision status and return normalized summary metadata.

    Args:
        trajectory: Trajectory-like object exposing joint positions.
        planning_scene: Optional planning-scene object with revision and ACM metadata.
        collision_obstacles: Legacy obstacle collection used when no planning scene is present.

    Returns:
        tuple[list[str], dict[str, object]]: Validation reasons and structured collision summary.

    Raises:
        None: Invalid or missing data is normalized into an empty collision result.
    """
    reasons: list[str] = []
    result = _collision_result(trajectory, planning_scene=planning_scene, collision_obstacles=collision_obstacles)
    summary = {
        'self_collision': result.self_collision,
        'environment_collision': result.environment_collision,
        'ignored_pairs': list(result.ignored_pairs),
        'checked_pairs': list(result.checked_pairs),
        'self_pairs': list(result.self_pairs),
        'environment_pairs': list(result.environment_pairs),
        'scene_revision': result.scene_revision,
        'collision_level': result.collision_level,
        'clearance_metric': result.clearance_metric,
        **dict(result.metadata),
    }
    if result.self_collision:
        reasons.append('self_collision_risk')
    if result.environment_collision:
        reasons.append('environment_collision_risk')
    return reasons, summary



def _collision_result(trajectory, *, collision_obstacles=(), planning_scene=None) -> CollisionResult:
    """Compute the collision result, using bounded caches for repeated evaluations."""
    trajectory_digest = _resolve_trajectory_digest(trajectory)
    if trajectory.joint_positions is None:
        return CollisionResult(
            scene_revision=int(getattr(planning_scene, 'revision', 0) or 0),
            collision_level=str(getattr(getattr(planning_scene, 'collision_level', None), 'value', getattr(planning_scene, 'collision_level', 'aabb'))),
            metadata=_backend_metadata(
                planning_scene,
                cache_hit=False,
                candidate_pair_count=0,
                geometry_cache_hit=False,
                trajectory_digest=trajectory_digest,
            ),
        )
    joint_positions = np.asarray(trajectory.joint_positions, dtype=float)
    link_names = [f'link_{i}' for i in range(max(joint_positions.shape[1] - 1, 0))]
    scene_revision = int(getattr(planning_scene, 'revision', 0) or 0)
    collision_level = str(getattr(getattr(planning_scene, 'collision_level', None), 'value', getattr(planning_scene, 'collision_level', 'aabb')))
    cache_key = _build_cache_key(
        trajectory_digest,
        planning_scene=planning_scene,
        collision_obstacles=collision_obstacles,
    )
    cached = _COLLISION_CACHE.get(cache_key)
    if cached is not None:
        assert isinstance(cached, CollisionResult)
        return replace(
            cached,
            metadata={
                **dict(cached.metadata),
                'cache_hit': True,
                'trajectory_digest': trajectory_digest,
            },
        )

    if planning_scene is not None:
        result = _evaluate_scene_collision(
            joint_positions,
            link_names=link_names,
            planning_scene=planning_scene,
            scene_revision=scene_revision,
            collision_level=collision_level,
            trajectory_digest=trajectory_digest,
        )
    else:
        result = _evaluate_legacy_collision(
            joint_positions,
            collision_obstacles=tuple(collision_obstacles),
            scene_revision=scene_revision,
            collision_level=collision_level,
            trajectory_digest=trajectory_digest,
        )
    _COLLISION_CACHE.put(cache_key, result)
    return result



def _evaluate_scene_collision(
    joint_positions: np.ndarray,
    *,
    link_names: list[str],
    planning_scene,
    scene_revision: int,
    collision_level: str,
    trajectory_digest: str,
) -> CollisionResult:
    """Evaluate collision status against a structured planning scene."""
    self_padding = float(getattr(planning_scene, 'self_collision_padding', 0.03) if planning_scene is not None else 0.03)
    ignore_adjacent = bool(getattr(planning_scene, 'ignore_adjacent_self_collisions', True) if planning_scene is not None else True)
    acm = getattr(planning_scene, 'allowed_collision_matrix', None)
    obstacles = list(getattr(planning_scene, 'obstacles', ()))
    backend = _resolve_backend_id(planning_scene)
    obstacle_pairs = [(str(obj.object_id), obj.geometry) for obj in obstacles]

    geometry, geometry_cache_hit = _scene_geometry(
        joint_positions,
        link_names=link_names,
        padding=self_padding,
        ignore_adjacent=ignore_adjacent,
        trajectory_digest=trajectory_digest,
    )

    ignored_pairs: set[tuple[str, str]] = set()
    checked_pairs: set[tuple[str, str]] = set()
    accepted_self_pairs: set[tuple[str, str]] = set()
    accepted_env_pairs: set[tuple[str, str]] = set()
    clearance_values: list[float] = []
    candidate_pair_count = 0
    self_pair_specs = _self_pair_specs(link_names, ignore_adjacent=ignore_adjacent)

    for self_boxes, seen_self in zip(geometry.frame_boxes, geometry.self_hits):
        frame_candidate_count = 0
        for i, j, pair in self_pair_specs:
            checked_pairs.add(pair)
            if acm is not None and acm.allows(*pair):
                ignored_pairs.add(pair)
                continue
            frame_candidate_count += 1
            clearance_values.append(self_boxes[i].distance(self_boxes[j]))
            if pair in seen_self:
                accepted_self_pairs.add(pair)

        for i, box_i in enumerate(self_boxes):
            link_name = str(link_names[i])
            for object_id, obstacle in obstacle_pairs:
                pair = (link_name, str(object_id))
                checked_pairs.add(pair)
                if acm is not None and acm.allows(*pair):
                    ignored_pairs.add(pair)
                    continue
                frame_candidate_count += 1
                clearance_values.append(box_i.distance(obstacle))
                if box_i.intersects(obstacle):
                    accepted_env_pairs.add(pair)
        candidate_pair_count += frame_candidate_count

    return CollisionResult(
        self_collision=bool(accepted_self_pairs),
        environment_collision=bool(accepted_env_pairs),
        self_pairs=tuple(sorted(accepted_self_pairs)),
        environment_pairs=tuple(sorted(accepted_env_pairs)),
        ignored_pairs=tuple(sorted(ignored_pairs)),
        checked_pairs=tuple(sorted(checked_pairs)),
        scene_revision=scene_revision,
        collision_level=collision_level,
        clearance_metric=float(min(clearance_values)) if clearance_values else 0.0,
        metadata=_backend_metadata(
            planning_scene,
            cache_hit=False,
            candidate_pair_count=candidate_pair_count,
            resolved_backend=backend,
            geometry_cache_hit=geometry_cache_hit,
            trajectory_digest=trajectory_digest,
        ),
    )



def _frame_link_boxes(frame: np.ndarray, *, padding: float) -> tuple[AABB, ...]:
    """Build per-link AABBs for one joint-position frame."""
    return tuple(aabb_from_points(frame[i:i + 2], padding=padding) for i in range(max(frame.shape[0] - 1, 0)))



def _self_pair_specs(link_names: list[str], *, ignore_adjacent: bool) -> tuple[tuple[int, int, tuple[str, str]], ...]:
    """Precompute canonical self-collision pair descriptors for a link chain."""
    pairs: list[tuple[int, int, tuple[str, str]]] = []
    for i in range(len(link_names)):
        for j in range(i + 1, len(link_names)):
            if ignore_adjacent and abs(i - j) <= 1:
                continue
            pairs.append((i, j, (str(link_names[i]), str(link_names[j]))))
    return tuple(pairs)



def _scene_geometry(
    joint_positions: np.ndarray,
    *,
    link_names: list[str],
    padding: float,
    ignore_adjacent: bool,
    trajectory_digest: str,
) -> tuple[_SceneFrameGeometry, bool]:
    """Return cached per-frame scene geometry for one trajectory digest."""
    key = (
        'scene_geometry',
        trajectory_digest,
        tuple(str(name) for name in link_names),
        round(float(padding), 8),
        bool(ignore_adjacent),
    )
    cached = _GEOMETRY_CACHE.get(key)
    if cached is not None:
        assert isinstance(cached, _SceneFrameGeometry)
        return cached, True
    built = _build_scene_frame_geometry(joint_positions, link_names=link_names, padding=padding, ignore_adjacent=ignore_adjacent)
    _GEOMETRY_CACHE.put(key, built)
    return built, False



def _build_scene_frame_geometry(
    joint_positions: np.ndarray,
    *,
    link_names: list[str],
    padding: float,
    ignore_adjacent: bool,
) -> _SceneFrameGeometry:
    """Precompute frame-local link AABBs and self-hit pairs.

    Args:
        joint_positions: Per-frame joint positions.
        link_names: Canonical link-name labels.
        padding: Self-collision padding applied to AABB generation.
        ignore_adjacent: Whether adjacent links are excluded from self checks.

    Returns:
        _SceneFrameGeometry: Cached frame geometry for repeated scene validation.

    Raises:
        None: Invalid shapes simply produce empty per-frame descriptors.
    """
    frame_boxes: list[tuple[AABB, ...]] = []
    self_hits: list[frozenset[tuple[str, str]]] = []
    for frame in joint_positions:
        boxes = _frame_link_boxes(np.asarray(frame, dtype=float), padding=padding)
        pair_indices = broad_phase_intersections(list(boxes))
        if ignore_adjacent:
            pair_indices = [(i, j) for i, j in pair_indices if abs(i - j) > 1]
        frame_boxes.append(boxes)
        self_hits.append(
            frozenset((str(link_names[i]), str(link_names[j])) for i, j in pair_indices)
        )
    return _SceneFrameGeometry(frame_boxes=tuple(frame_boxes), self_hits=tuple(self_hits))



def _evaluate_legacy_collision(
    joint_positions: np.ndarray,
    *,
    collision_obstacles: tuple[object, ...],
    scene_revision: int,
    collision_level: str,
    trajectory_digest: str,
) -> CollisionResult:
    """Evaluate collision status against the legacy obstacle list."""
    checked_pairs: set[tuple[str, str]] = set()
    accepted_env_pairs: set[tuple[str, str]] = set()
    clearance_values: list[float] = []
    env_padding = 0.02
    candidate_pair_count = 0
    geometry, geometry_cache_hit = _legacy_geometry(joint_positions, padding=env_padding, trajectory_digest=trajectory_digest)
    for frame, robot_box in zip(joint_positions, geometry.robot_boxes):
        env_flags = environment_collision_flags(frame[None, ...], list(collision_obstacles), padding=env_padding)
        frame_candidate_count = 0
        for idx, obstacle in enumerate(collision_obstacles):
            pair = ('robot', f'environment_{idx}')
            checked_pairs.add(pair)
            frame_candidate_count += 1
            if isinstance(obstacle, AABB):
                clearance_values.append(robot_box.distance(obstacle))
        if any(env_flags):
            accepted_env_pairs.add(('robot', 'environment'))
            checked_pairs.add(('robot', 'environment'))
        candidate_pair_count += frame_candidate_count

    return CollisionResult(
        self_collision=False,
        environment_collision=bool(accepted_env_pairs),
        self_pairs=(),
        environment_pairs=tuple(sorted(accepted_env_pairs)),
        ignored_pairs=(),
        checked_pairs=tuple(sorted(checked_pairs)),
        scene_revision=scene_revision,
        collision_level=collision_level,
        clearance_metric=float(min(clearance_values)) if clearance_values else 0.0,
        metadata={
            'requested_backend': 'legacy',
            'resolved_backend': 'legacy',
            'backend_available': True,
            'cache_hit': False,
            'geometry_cache_hit': bool(geometry_cache_hit),
            'candidate_pair_count': int(candidate_pair_count),
            'trajectory_digest': trajectory_digest,
        },
    )



def _legacy_geometry(joint_positions: np.ndarray, *, padding: float, trajectory_digest: str) -> tuple[_LegacyFrameGeometry, bool]:
    """Return cached legacy robot AABBs for one trajectory digest."""
    key = ('legacy_geometry', trajectory_digest, round(float(padding), 8))
    cached = _GEOMETRY_CACHE.get(key)
    if cached is not None:
        assert isinstance(cached, _LegacyFrameGeometry)
        return cached, True
    built = _LegacyFrameGeometry(
        robot_boxes=tuple(aabb_from_points(np.asarray(frame, dtype=float), padding=padding) for frame in joint_positions),
    )
    _GEOMETRY_CACHE.put(key, built)
    return built, False



def _resolve_backend_id(planning_scene) -> str:
    requested_backend = str(getattr(planning_scene, 'collision_backend', _COLLISION_BACKEND_REGISTRY.default_backend) or _COLLISION_BACKEND_REGISTRY.default_backend)
    resolved_backend, _ = _COLLISION_BACKEND_REGISTRY.normalize_backend(
        requested_backend,
        metadata=dict(getattr(planning_scene, 'metadata', {}) or {}),
    )
    return resolved_backend



def _backend_metadata(
    planning_scene,
    *,
    cache_hit: bool,
    candidate_pair_count: int,
    resolved_backend: str | None = None,
    geometry_cache_hit: bool | None = None,
    trajectory_digest: str | None = None,
) -> dict[str, object]:
    metadata = dict(getattr(planning_scene, 'metadata', {}) if planning_scene is not None else {})
    requested_backend = str(metadata.get('requested_collision_backend', getattr(planning_scene, 'collision_backend', _COLLISION_BACKEND_REGISTRY.default_backend)) or _COLLISION_BACKEND_REGISTRY.default_backend).strip().lower() if planning_scene is not None else 'aabb'
    backend_id = resolved_backend or _resolve_backend_id(planning_scene)
    payload = {
        'requested_backend': requested_backend,
        'resolved_backend': backend_id,
        'backend_available': backend_id == requested_backend,
        'cache_hit': bool(cache_hit),
        'candidate_pair_count': int(candidate_pair_count),
    }
    if geometry_cache_hit is not None:
        payload['geometry_cache_hit'] = bool(geometry_cache_hit)
    if trajectory_digest:
        payload['trajectory_digest'] = str(trajectory_digest)
    warning = metadata.get('collision_backend_warning')
    if warning:
        payload['collision_backend_warning'] = str(warning)
    return payload



def _build_cache_key(trajectory_digest: str, *, planning_scene=None, collision_obstacles=()) -> tuple[object, ...]:
    payload = {
        'trajectory_digest': str(trajectory_digest),
        'scene_revision': int(getattr(planning_scene, 'revision', 0) or 0),
        'collision_backend': str(getattr(planning_scene, 'collision_backend', 'none') if planning_scene is not None else 'none'),
        'obstacles_digest': _digest_obstacles(planning_scene=planning_scene, collision_obstacles=collision_obstacles),
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
    return ('collision_result', digest)



def _resolve_trajectory_digest(trajectory) -> str:
    """Return a stable digest for the evaluated trajectory."""
    return ensure_trajectory_digest_metadata(trajectory)



def _digest_obstacles(*, planning_scene=None, collision_obstacles=()) -> tuple[object, ...]:
    if planning_scene is not None:
        obstacles = []
        for obstacle in getattr(planning_scene, 'obstacles', ()):
            geometry = getattr(obstacle, 'geometry', None)
            obstacles.append((str(getattr(obstacle, 'object_id', '')), _digest_geometry(geometry)))
        return tuple(obstacles)
    legacy = []
    for index, obstacle in enumerate(collision_obstacles):
        legacy.append((index, _digest_geometry(obstacle)))
    return tuple(legacy)



def _digest_geometry(geometry: object) -> dict[str, object]:
    if isinstance(geometry, AABB):
        return {
            'kind': 'aabb',
            'minimum': tuple(float(v) for v in np.asarray(geometry.minimum, dtype=float).tolist()),
            'maximum': tuple(float(v) for v in np.asarray(geometry.maximum, dtype=float).tolist()),
        }
    if geometry is None:
        return {'kind': 'none'}
    minimum = getattr(geometry, 'minimum', None)
    maximum = getattr(geometry, 'maximum', None)
    if minimum is not None and maximum is not None:
        return {
            'kind': type(geometry).__name__.lower(),
            'minimum': tuple(float(v) for v in np.asarray(minimum, dtype=float).tolist()),
            'maximum': tuple(float(v) for v in np.asarray(maximum, dtype=float).tolist()),
        }
    return {'kind': type(geometry).__name__, 'repr': repr(geometry)}
