from __future__ import annotations

import numpy as np

from robot_sim.application.validators.collision_validator import evaluate_collision_summary
from robot_sim.application.validators.goal_validator import evaluate_goal_metrics
from robot_sim.application.validators.limit_validator import evaluate_limit_summary
from robot_sim.application.validators.path_metrics import evaluate_path_metrics
from robot_sim.application.validators.timing_validator import evaluate_timing_summary
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.model.diagnostics_report import TrajectoryDiagnosticsReport
from robot_sim.model.pose import Pose
from robot_sim.model.trajectory import JointTrajectory


class ValidateTrajectoryUseCase:
    """Validate trajectory timing, limits, collisions, and goal metrics."""

    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()

    def execute(
        self,
        trajectory: JointTrajectory,
        *,
        collision_obstacles: tuple[object, ...] = (),
        target_pose=None,
        spec=None,
        q_goal=None,
        planning_scene=None,
    ) -> TrajectoryDiagnosticsReport:
        """Validate a trajectory and return diagnostics.

        Args:
            trajectory: Planned joint trajectory.
            collision_obstacles: Legacy collision obstacle collection.
            target_pose: Optional explicit target pose.
            spec: Optional robot specification used for FK fallback.
            q_goal: Optional goal joint vector used to recover target pose.
            planning_scene: Optional planning scene used for collision checks.

        Returns:
            Structured trajectory diagnostics report.
        """
        reasons: list[str] = []
        q = np.asarray(trajectory.q, dtype=float)
        qd = np.asarray(trajectory.qd, dtype=float)
        qdd = np.asarray(trajectory.qdd, dtype=float)
        t = np.asarray(trajectory.t, dtype=float)
        if np.isnan(q).any() or np.isnan(qd).any() or np.isnan(qdd).any():
            reasons.append('nan_values')
        if np.isinf(q).any() or np.isinf(qd).any() or np.isinf(qdd).any():
            reasons.append('inf_values')

        extra_reasons, timing_summary = evaluate_timing_summary(t)
        reasons.extend(extra_reasons)

        ee_positions = None if trajectory.ee_positions is None else np.asarray(trajectory.ee_positions, dtype=float)
        ee_rotations = None if trajectory.ee_rotations is None else np.asarray(trajectory.ee_rotations, dtype=float)
        cache_errors = tuple(getattr(trajectory, 'cache_integrity_errors', lambda: ())())
        cache_used = bool(trajectory.has_complete_fk_cache)
        cache_miss_reason = ''
        if spec is not None and q.shape[0] >= 1 and not trajectory.has_complete_fk_cache:
            if cache_errors:
                cache_miss_reason = 'shape_mismatch'
            elif trajectory.cache_status == 'partial':
                cache_miss_reason = 'plugin_partial_cache'
            else:
                cache_miss_reason = 'missing_cached_fk'
            ee_positions = []
            ee_rotations = []
            for q_i in q:
                fk = self._fk.solve(spec, q_i)
                ee_positions.append(fk.ee_pose.p)
                ee_rotations.append(fk.ee_pose.R)
            ee_positions = np.asarray(ee_positions, dtype=float)
            ee_rotations = np.asarray(ee_rotations, dtype=float)
            cache_used = False

        metrics = evaluate_path_metrics(q=q, qd=qd, qdd=qdd, t=t, ee_positions=ee_positions, ee_rotations=ee_rotations)

        resolved_target_pose = target_pose
        goal_pose_source = 'explicit_target' if resolved_target_pose is not None else ''
        if resolved_target_pose is None and spec is not None and q_goal is not None:
            q_goal_array = np.asarray(q_goal, dtype=float)
            can_reuse_terminal_fk = (
                ee_positions is not None
                and ee_rotations is not None
                and q.shape[0] >= 1
                and ee_positions.shape[0] == q.shape[0]
                and ee_rotations.shape[0] == q.shape[0]
                and q_goal_array.shape == q[-1].shape
                and np.allclose(q_goal_array, q[-1], atol=1.0e-9, rtol=1.0e-7)
            )
            if can_reuse_terminal_fk:
                resolved_target_pose = Pose(
                    p=np.asarray(ee_positions[-1], dtype=float).copy(),
                    R=np.asarray(ee_rotations[-1], dtype=float).copy(),
                )
                goal_pose_source = 'cached_terminal_fk'
            else:
                goal_fk = self._fk.solve(spec, q_goal_array)
                resolved_target_pose = goal_fk.ee_pose
                goal_pose_source = 'fk_goal_projection'
        goal_metrics = evaluate_goal_metrics(ee_positions=ee_positions, ee_rotations=ee_rotations, target_pose=resolved_target_pose)

        extra_reasons, collision_summary = evaluate_collision_summary(trajectory, planning_scene=planning_scene, collision_obstacles=collision_obstacles)
        reasons.extend(extra_reasons)

        extra_reasons, limit_summary = evaluate_limit_summary(q, spec)
        reasons.extend(extra_reasons)

        feasible = not reasons
        metadata = {
            'num_samples': int(t.shape[0]),
            'dof': int(q.shape[1]) if q.ndim == 2 else 0,
            'collision_summary': collision_summary,
            'limit_summary': limit_summary,
            'timing_summary': timing_summary,
            'goal_pose_available': bool(resolved_target_pose is not None),
            'goal_pose_source': goal_pose_source,
            'cache_used': bool(cache_used),
            'cache_miss_reason': cache_miss_reason,
        }
        if planning_scene is not None:
            metadata['scene_revision'] = int(getattr(planning_scene, 'revision', 0))
        return TrajectoryDiagnosticsReport(
            feasible=feasible,
            reasons=tuple(reasons),
            max_velocity=float(metrics['max_velocity']),
            max_acceleration=float(metrics['max_acceleration']),
            jerk_proxy=float(metrics['jerk_proxy']),
            goal_position_error=float(goal_metrics['goal_position_error']),
            goal_orientation_error=float(goal_metrics['goal_orientation_error']),
            start_to_end_position_delta=float(metrics['start_to_end_position_delta']),
            start_to_end_orientation_delta=float(metrics['start_to_end_orientation_delta']),
            path_length=float(metrics['path_length']),
            metadata=metadata,
        )
