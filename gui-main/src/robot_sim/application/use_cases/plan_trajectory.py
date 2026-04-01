from __future__ import annotations

from collections.abc import Callable

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.pipelines.trajectory_pipeline import TrajectoryExecutionPipeline
from robot_sim.application.trajectory_metadata import build_planner_metadata
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.trajectory.registry import TrajectoryPlannerRegistry
from robot_sim.domain.errors import CancelledTaskError
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.trajectory_digest import ensure_trajectory_digest_metadata
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class PlanTrajectoryUseCase:
    """Application use case that plans and validates robot trajectories."""

    def __init__(self, planner_registry: TrajectoryPlannerRegistry, version_catalog: VersionCatalog | None = None) -> None:
        """Create the trajectory-planning use case.

        Args:
            planner_registry: Planner registry used to resolve planning plugins.
            version_catalog: Optional version catalog used for export metadata.

        Returns:
            None: Initializes planning dependencies only.

        Raises:
            ValueError: If ``planner_registry`` is not provided.
        """
        if planner_registry is None:
            raise ValueError('PlanTrajectoryUseCase requires an explicit planner registry')
        self._validate_uc = ValidateTrajectoryUseCase()
        self._planner_registry = planner_registry
        self._pipeline = TrajectoryExecutionPipeline(planner_registry, self._validate_uc)
        self._versions = version_catalog or current_version_catalog()

    def _resolve_planner_id(self, req: TrajectoryRequest) -> str:
        return self._pipeline.resolve_planner_id(req)

    def execute(
        self,
        req: TrajectoryRequest,
        *,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[float, str, dict[str, object] | None], None] | None = None,
        correlation_id: str | None = None,
    ) -> JointTrajectory:
        """Plan, retime, and validate a trajectory request."""
        if cancel_flag is not None and bool(cancel_flag()):
            raise CancelledTaskError('trajectory planning cancelled')
        planner_id = self._resolve_planner_id(req)
        if progress_cb is not None:
            progress_cb(5.0, 'resolved planner', {'planner_id': planner_id, 'correlation_id': str(correlation_id or '')})
        pipeline_result = self._pipeline.execute(req)
        if cancel_flag is not None and bool(cancel_flag()):
            raise CancelledTaskError('trajectory planning cancelled')
        traj = pipeline_result.retimed
        diagnostics = pipeline_result.diagnostics
        quality = {
            'max_velocity': diagnostics.max_velocity,
            'max_acceleration': diagnostics.max_acceleration,
            'jerk_proxy': diagnostics.jerk_proxy,
            'path_length': diagnostics.path_length,
            'goal_position_error': diagnostics.goal_position_error,
            'goal_orientation_error': diagnostics.goal_orientation_error,
            'start_to_end_position_delta': diagnostics.start_to_end_position_delta,
            'start_to_end_orientation_delta': diagnostics.start_to_end_orientation_delta,
            'endpoint_position_error': diagnostics.goal_position_error,
            'endpoint_orientation_error': diagnostics.goal_orientation_error,
        }
        feasibility = {
            'feasible': diagnostics.feasible,
            'reasons': list(diagnostics.reasons),
            'collision_summary': dict(diagnostics.metadata.get('collision_summary', {})),
            'limit_summary': dict(diagnostics.metadata.get('limit_summary', {})),
            'timing_summary': dict(diagnostics.metadata.get('timing_summary', {})),
        }
        metadata = build_planner_metadata(
            planner_id=planner_id,
            goal_source=str(traj.metadata.get('goal_source', 'joint_space') or 'joint_space'),
            cache_status=pipeline_result.cache_status,
            mode=str(getattr(req.mode, 'value', req.mode)),
            metadata=dict(traj.metadata),
            scene_revision=pipeline_result.scene_revision,
            validation_stage=pipeline_result.validation_stage,
            correlation_id=correlation_id,
            has_complete_fk=bool(traj.ee_positions is not None and traj.joint_positions is not None and traj.ee_rotations is not None),
            has_partial_fk=bool(traj.ee_positions is not None or traj.joint_positions is not None or traj.ee_rotations is not None),
        )
        metadata.setdefault('export_version', self._versions.export_schema_version)
        metadata.setdefault('goal_pose_available', bool(diagnostics.metadata.get('goal_pose_available', False)))
        metadata['phase_timings_ms'] = dict(pipeline_result.phase_timings_ms)
        metadata.setdefault('path_stage', planner_id)
        metadata['retiming_applied'] = bool(metadata.get('retimed', False))
        metadata.setdefault('retimer_id', 'builtin_scaling')
        if req.max_velocity is not None:
            metadata['requested_max_velocity'] = float(req.max_velocity)
        if req.max_acceleration is not None:
            metadata['requested_max_acceleration'] = float(req.max_acceleration)
        if progress_cb is not None:
            progress_cb(
                100.0,
                'trajectory planned',
                {'planner_id': planner_id, 'cache_status': metadata['cache_status'], 'correlation_id': str(correlation_id or '')},
            )
        planned = JointTrajectory(
            t=traj.t,
            q=traj.q,
            qd=traj.qd,
            qdd=traj.qdd,
            ee_positions=traj.ee_positions,
            joint_positions=traj.joint_positions,
            ee_rotations=traj.ee_rotations,
            metadata=metadata,
            feasibility=feasibility,
            quality=quality,
        )
        if planned.cache_integrity_errors():
            planned.metadata['cache_integrity_errors'] = list(planned.cache_integrity_errors())
            planned.metadata['cache_status'] = 'partial' if planned.has_any_fk_cache else 'none'
        ensure_trajectory_digest_metadata(planned)
        return planned
