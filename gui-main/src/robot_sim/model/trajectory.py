from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.trajectory_digest import ensure_trajectory_digest_metadata
from robot_sim.domain.types import FloatArray
from robot_sim.model.trajectory_feasibility import TrajectoryFeasibility
from robot_sim.model.trajectory_quality import TrajectoryQuality


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def _coerce_reason_items(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if value in (None, ''):
        return ()
    return (str(value),)


def _sample_count(array: object) -> int | None:
    shape = getattr(array, 'shape', None)
    if isinstance(shape, tuple) and shape:
        try:
            return int(shape[0])
        except (TypeError, ValueError):
            return None
    return None


@dataclass(frozen=True)
class JointTrajectory:
    """Sampled robot joint trajectory with optional cached FK data."""

    t: FloatArray
    q: FloatArray
    qd: FloatArray
    qdd: FloatArray
    ee_positions: FloatArray | None = None
    joint_positions: FloatArray | None = None
    ee_rotations: FloatArray | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    feasibility: dict[str, object] = field(default_factory=dict)
    quality: dict[str, object] = field(default_factory=dict)

    @property
    def sample_count(self) -> int:
        """Return the number of trajectory samples.

        Returns:
            int: Number of time-indexed samples.

        Raises:
            ValueError: If ``t`` does not expose a leading dimension.
        """
        count = _sample_count(self.t)
        if count is None:
            raise ValueError('trajectory.t does not expose a valid sample dimension')
        return count

    def cache_integrity_errors(self) -> tuple[str, ...]:
        """Validate cached FK arrays against the trajectory sample count.

        Returns:
            tuple[str, ...]: Canonical cache-integrity error identifiers.

        Raises:
            None: Pure deterministic validation.
        """
        errors: list[str] = []
        expected = self.sample_count
        for field_name, value in (
            ('ee_positions', self.ee_positions),
            ('joint_positions', self.joint_positions),
            ('ee_rotations', self.ee_rotations),
        ):
            if value is None:
                continue
            count = _sample_count(value)
            if count is None:
                errors.append(f'{field_name}_invalid_shape')
                continue
            if count != expected:
                errors.append(f'{field_name}_length_mismatch')
        return tuple(errors)

    @property
    def has_cached_fk(self) -> bool:
        """Return whether end-effector positions are cached for any samples."""
        return self.ee_positions is not None

    @property
    def has_cached_joint_positions(self) -> bool:
        """Return whether per-frame joint positions are cached for any samples."""
        return self.joint_positions is not None

    @property
    def has_cached_rotations(self) -> bool:
        """Return whether end-effector rotations are cached for any samples."""
        return self.ee_rotations is not None

    @property
    def has_any_fk_cache(self) -> bool:
        """Return whether any FK-related cache array is present."""
        return bool(self.ee_positions is not None or self.joint_positions is not None or self.ee_rotations is not None)

    @property
    def has_complete_fk_cache(self) -> bool:
        """Return whether all playback-critical FK caches are present and shape aligned."""
        return (
            self.ee_positions is not None
            and self.joint_positions is not None
            and self.ee_rotations is not None
            and not self.cache_integrity_errors()
        )

    @property
    def is_playback_ready(self) -> bool:
        """Return whether the trajectory can be consumed by playback without recomputation."""
        return self.has_complete_fk_cache

    @property
    def cache_status(self) -> str:
        """Return the normalized FK cache status string.

        Returns:
            str: One of ``none``, ``partial``, ``ready``, or ``recomputed``.

        Raises:
            None: Pure deterministic normalization.
        """
        value = str(self.metadata.get('cache_status', '') or '').strip().lower()
        if self.has_complete_fk_cache:
            return 'recomputed' if value == 'recomputed' else 'ready'
        if self.has_any_fk_cache:
            return 'partial'
        return 'none'

    @property
    def typed_quality(self) -> TrajectoryQuality:
        return TrajectoryQuality(
            max_velocity=_coerce_float(self.quality.get('max_velocity', self.quality.get('max_abs_qd', 0.0))),
            max_acceleration=_coerce_float(self.quality.get('max_acceleration', self.quality.get('max_abs_qdd', 0.0))),
            jerk_proxy=_coerce_float(self.quality.get('jerk_proxy', 0.0)),
            path_length=_coerce_float(self.quality.get('path_length', 0.0)),
            goal_position_error=_coerce_float(self.quality.get('goal_position_error', 0.0)),
            goal_orientation_error=_coerce_float(self.quality.get('goal_orientation_error', 0.0)),
            start_to_end_position_delta=_coerce_float(self.quality.get('start_to_end_position_delta', 0.0)),
            start_to_end_orientation_delta=_coerce_float(self.quality.get('start_to_end_orientation_delta', 0.0)),
            singularity_exposure=_coerce_float(self.quality.get('singularity_exposure', 0.0)),
        )

    @property
    def typed_feasibility(self) -> TrajectoryFeasibility:
        return TrajectoryFeasibility(
            feasible=bool(self.feasibility.get('feasible', True)),
            reasons=_coerce_reason_items(self.feasibility.get('reasons', ())),
            collision_summary=_coerce_mapping(self.feasibility.get('collision_summary', {})),
            limit_summary=_coerce_mapping(self.feasibility.get('limit_summary', {})),
            timing_summary=_coerce_mapping(self.feasibility.get('timing_summary', {})),
        )

    @property
    def goal_position_error(self) -> float:
        return self.typed_quality.goal_position_error

    @property
    def goal_orientation_error(self) -> float:
        return self.typed_quality.goal_orientation_error

    @property
    def start_to_end_position_delta(self) -> float:
        return self.typed_quality.start_to_end_position_delta

    @property
    def start_to_end_orientation_delta(self) -> float:
        return self.typed_quality.start_to_end_orientation_delta

    @property
    def collision_summary(self) -> dict[str, object]:
        return self.typed_feasibility.collision_summary

    @property
    def timing_summary(self) -> dict[str, object]:
        return self.typed_feasibility.timing_summary

    @property
    def limit_summary(self) -> dict[str, object]:
        return self.typed_feasibility.limit_summary

    @property
    def trajectory_digest(self) -> str:
        """Return a stable digest for the trajectory content and cached FK state."""
        return ensure_trajectory_digest_metadata(self)

    @property
    def scene_revision(self) -> int:
        value = self.metadata.get('scene_revision', 0)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    @property
    def ignored_collision_pairs(self) -> tuple[tuple[str, str], ...]:
        pairs = self.collision_summary.get('ignored_pairs', ())
        if not isinstance(pairs, (list, tuple)):
            return ()
        normalized: list[tuple[str, str]] = []
        for pair in pairs:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                normalized.append((str(pair[0]), str(pair[1])))
        return tuple(normalized)
