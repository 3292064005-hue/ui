from __future__ import annotations

from robot_sim.domain.enums import PlannerFamily

_CANONICAL_CACHE_STATUSES = {"none", "partial", "ready", "recomputed"}


def infer_planner_family(planner_id: str, goal_source: str = '') -> str:
    """Infer a stable planner-family label from planner identity and goal space.

    Args:
        planner_id: Canonical planner identifier.
        goal_source: Goal-space hint already present in trajectory metadata.

    Returns:
        Canonical planner-family string.

    Raises:
        None: This helper is a pure deterministic projection.
    """
    planner_key = str(planner_id or '').strip().lower()
    goal_key = str(goal_source or '').strip().lower()
    if planner_key == 'waypoint_graph' or goal_key == 'waypoint_graph':
        return PlannerFamily.WAYPOINT_GRAPH.value
    if 'cartesian' in planner_key or goal_key in {'cartesian_pose', 'cartesian'}:
        return PlannerFamily.CARTESIAN.value
    return PlannerFamily.JOINT.value


def normalize_cache_status(cache_status: object, *, has_complete_fk: bool = False, has_partial_fk: bool = False) -> str:
    """Normalize FK cache-state metadata to the canonical value set.

    Args:
        cache_status: Raw cache-status value.
        has_complete_fk: Whether full FK caches are available.
        has_partial_fk: Whether partial FK caches are available.

    Returns:
        Canonical cache-status string.

    Raises:
        None: This helper is a pure deterministic projection.
    """
    value = str(cache_status or '').strip().lower()
    if has_complete_fk:
        return 'recomputed' if value == 'recomputed' else 'ready'
    if has_partial_fk:
        return 'partial'
    if value in _CANONICAL_CACHE_STATUSES:
        return 'none' if value in {'ready', 'partial', 'recomputed'} else value
    return 'none'


def resolve_planner_metadata(metadata: dict[str, object] | None = None) -> dict[str, str]:
    """Resolve canonical planner metadata while confining legacy aliases to the edge.

    Args:
        metadata: Raw trajectory metadata payload.

    Returns:
        dict[str, str]: Canonical planner metadata keys.

    Raises:
        None: Resolution is a pure normalization step.
    """
    payload = dict(metadata or {})
    planner_id = str(payload.get('planner_id', payload.get('planner_type', payload.get('mode', 'unknown'))) or 'unknown')
    goal_source = str(payload.get('goal_source', payload.get('mode', 'unknown')) or 'unknown')
    planner_family = str(payload.get('planner_family', infer_planner_family(planner_id, goal_source)) or infer_planner_family(planner_id, goal_source))
    cache_status = normalize_cache_status(payload.get('cache_status', 'none'))
    return {
        'planner_id': planner_id,
        'planner_family': planner_family,
        'goal_source': goal_source,
        'cache_status': cache_status,
        'scene_revision': str(payload.get('scene_revision', '0') or '0'),
        'validation_stage': str(payload.get('validation_stage', '') or ''),
        'correlation_id': str(payload.get('correlation_id', '') or ''),
    }


def build_planner_metadata(
    *,
    planner_id: str,
    goal_source: str,
    cache_status: object = 'none',
    mode: str | None = None,
    metadata: dict[str, object] | None = None,
    scene_revision: int | None = None,
    validation_stage: str | None = None,
    correlation_id: str | None = None,
    has_complete_fk: bool = False,
    has_partial_fk: bool = False,
) -> dict[str, object]:
    """Build canonical planner metadata while preserving legacy aliases.

    Args:
        planner_id: Canonical planner identifier.
        goal_source: Goal-space label.
        cache_status: Raw cache-state value.
        mode: Optional trajectory mode string.
        metadata: Existing metadata payload to extend.
        scene_revision: Optional planning-scene revision.
        validation_stage: Optional validation stage label.
        correlation_id: Optional correlation identifier.
        has_complete_fk: Whether complete FK caches are available.
        has_partial_fk: Whether partial FK caches are available.

    Returns:
        Canonicalized planner metadata dictionary.

    Raises:
        None: This helper only normalizes metadata.
    """
    payload = dict(metadata or {})
    canonical_planner_id = str(planner_id)
    canonical_goal_source = str(goal_source)
    canonical_family = infer_planner_family(canonical_planner_id, canonical_goal_source)
    payload['planner_id'] = canonical_planner_id
    payload['planner_type'] = canonical_planner_id
    payload['planner_family'] = canonical_family
    payload['goal_source'] = canonical_goal_source
    payload['cache_status'] = normalize_cache_status(
        payload.get('cache_status', cache_status),
        has_complete_fk=has_complete_fk,
        has_partial_fk=has_partial_fk,
    )
    payload['correlation_id'] = str(correlation_id or payload.get('correlation_id', '') or '')
    if mode is not None and str(mode):
        payload.setdefault('mode', str(mode))
    if scene_revision is not None:
        payload['scene_revision'] = int(scene_revision)
    if validation_stage is not None and str(validation_stage):
        payload['validation_stage'] = str(validation_stage)
    return payload
