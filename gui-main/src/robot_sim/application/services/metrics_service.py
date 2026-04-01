from __future__ import annotations

import numpy as np

from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.ik_result import IKResult
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.model.trajectory import JointTrajectory


class MetricsService:
    def summarize_ik(self, result: IKResult) -> dict[str, float | int | bool | str]:
        final_pos_err = float(result.final_pos_err)
        final_ori_err = float(result.final_ori_err)
        final_cond = float(result.final_cond)
        final_manip = float(result.final_manipulability)
        final_dq = float(result.final_dq_norm)
        elapsed_ms = float(result.elapsed_ms)
        final_damping = float(result.diagnostics.get('damping_lambda', 0.0)) if result.diagnostics else 0.0
        if result.logs:
            last = result.logs[-1]
            if not np.isfinite(final_pos_err):
                final_pos_err = float(last.pos_err_norm)
            if not np.isfinite(final_ori_err):
                final_ori_err = float(last.ori_err_norm)
            if not np.isfinite(final_cond):
                final_cond = float(last.cond_number)
            if not np.isfinite(final_manip):
                final_manip = float(last.manipulability)
            if not np.isfinite(final_dq):
                final_dq = float(last.dq_norm)
            if elapsed_ms <= 0.0:
                elapsed_ms = float(last.elapsed_ms)
            if final_damping <= 0.0:
                final_damping = float(last.damping_lambda)
        return {
            'success': result.success,
            'iterations': len(result.logs),
            'final_pos_err': final_pos_err,
            'final_ori_err': final_ori_err,
            'final_cond': final_cond,
            'final_manipulability': final_manip,
            'final_dq_norm': final_dq,
            'elapsed_ms': elapsed_ms,
            'message': result.message,
            'stop_reason': result.stop_reason,
            'restarts_used': int(result.restarts_used),
            'effective_mode': result.effective_mode or (result.logs[-1].effective_mode if result.logs else ''),
            'final_damping': final_damping,
        }

    def summarize_trajectory(self, trajectory: JointTrajectory) -> dict[str, float | int | bool | str]:
        duration = float(trajectory.t[-1] - trajectory.t[0]) if trajectory.t.size else 0.0
        jerk_proxy = float(trajectory.typed_quality.jerk_proxy)
        if jerk_proxy == 0.0 and trajectory.qdd.shape[0] >= 2 and duration > 0.0:
            dt = np.diff(trajectory.t)
            if dt.size:
                jerk = np.diff(trajectory.qdd, axis=0) / np.maximum(dt[:, None], 1.0e-12)
                jerk_proxy = float(np.max(np.abs(jerk))) if jerk.size else 0.0
        path_length = float(trajectory.typed_quality.path_length)
        if path_length == 0.0 and trajectory.ee_positions is not None:
            ee = np.asarray(trajectory.ee_positions, dtype=float)
            if ee.shape[0] >= 2:
                path_length = float(np.sum(np.linalg.norm(np.diff(ee, axis=0), axis=1)))
        collision_summary = trajectory.typed_feasibility.collision_summary
        timing_summary = trajectory.typed_feasibility.timing_summary
        canonical = resolve_planner_metadata(trajectory.metadata)
        return {
            'num_samples': int(trajectory.t.shape[0]),
            'dof': int(trajectory.q.shape[1]),
            'duration': duration,
            'max_abs_q': float(np.max(np.abs(trajectory.q))) if trajectory.q.size else 0.0,
            'max_abs_qd': float(np.max(np.abs(trajectory.qd))) if trajectory.qd.size else 0.0,
            'max_abs_qdd': float(np.max(np.abs(trajectory.qdd))) if trajectory.qdd.size else 0.0,
            'jerk_proxy': jerk_proxy,
            'path_length': path_length,
            'goal_position_error': float(trajectory.typed_quality.goal_position_error),
            'goal_orientation_error': float(trajectory.typed_quality.goal_orientation_error),
            'start_to_end_position_delta': float(trajectory.typed_quality.start_to_end_position_delta),
            'start_to_end_orientation_delta': float(trajectory.typed_quality.start_to_end_orientation_delta),
            'endpoint_position_error': float(trajectory.typed_quality.goal_position_error),
            'endpoint_orientation_error': float(trajectory.typed_quality.goal_orientation_error),
            'cached_fk': bool(trajectory.ee_positions is not None and trajectory.joint_positions is not None),
            'mode': canonical['goal_source'],
            'planner_type': canonical['planner_id'],
            'retimed': bool(trajectory.metadata.get('retimed', False)),
            'retime_scale': float(trajectory.metadata.get('retime_scale', 1.0)),
            'goal_pose_available': bool(trajectory.metadata.get('goal_pose_available', False)),
            'cache_status': str(getattr(trajectory, 'cache_status', trajectory.metadata.get('cache_status', 'unknown'))),
            'feasible': bool(trajectory.typed_feasibility.feasible),
            'feasibility_reasons': ','.join(trajectory.typed_feasibility.reasons),
            'self_collision': bool(collision_summary.get('self_collision', False)),
            'environment_collision': bool(collision_summary.get('environment_collision', False)),
            'ignored_collision_pairs_count': int(len(collision_summary.get('ignored_pairs', ()))) if collision_summary else 0,
            'scene_revision': int(collision_summary.get('scene_revision', trajectory.scene_revision)) if collision_summary else int(trajectory.scene_revision),
            'timing_monotonic': bool(timing_summary.get('monotonic_time', True)),
        }

    def summarize_batch(self, results: list[IKResult]) -> dict[str, float]:
        if not results:
            return {'count': 0.0, 'success_rate': 0.0}
        success = np.array([1.0 if r.success else 0.0 for r in results], dtype=float)
        pos = np.array([r.final_pos_err for r in results if np.isfinite(r.final_pos_err)], dtype=float)
        ori = np.array([r.final_ori_err for r in results if np.isfinite(r.final_ori_err)], dtype=float)
        cond = np.array([r.final_cond for r in results if np.isfinite(r.final_cond)], dtype=float)
        restarts = np.array([r.restarts_used for r in results], dtype=float)
        return {
            'count': float(len(results)),
            'success_rate': float(success.mean()),
            'mean_final_pos_err': float(pos.mean()) if pos.size else float('nan'),
            'mean_final_ori_err': float(ori.mean()) if ori.size else float('nan'),
            'mean_final_cond': float(cond.mean()) if cond.size else float('nan'),
            'mean_restarts_used': float(restarts.mean()) if restarts.size else 0.0,
        }

    def summarize_benchmark(self, report: BenchmarkReport) -> dict[str, float | int | str | bool]:
        return {
            'robot': report.robot,
            'num_cases': int(report.num_cases),
            'success_rate': float(report.success_rate),
            'p50_elapsed_ms': float(report.aggregate.get('p50_elapsed_ms', 0.0)),
            'p95_elapsed_ms': float(report.aggregate.get('p95_elapsed_ms', 0.0)),
            'mean_final_pos_err': float(report.aggregate.get('mean_final_pos_err', float('nan'))),
            'mean_final_ori_err': float(report.aggregate.get('mean_final_ori_err', float('nan'))),
            'mean_restarts_used': float(report.aggregate.get('mean_restarts_used', 0.0)),
            'regressed': bool(report.comparison.get('regressed', False)),
        }

    def summarize_task(self, snapshot: TaskSnapshot | None) -> dict[str, object]:
        if snapshot is None:
            return {'task_state': 'idle', 'task_kind': '', 'progress_percent': 0.0}
        return {
            'task_id': snapshot.task_id,
            'task_kind': snapshot.task_kind,
            'task_state': snapshot.task_state.value,
            'progress_stage': snapshot.progress_stage,
            'progress_percent': float(snapshot.progress_percent),
            'message': snapshot.message,
            'stop_reason': snapshot.stop_reason,
        }

    def summarize_scene(self, scene) -> dict[str, object]:
        if scene is None:
            return {'revision': 0, 'obstacle_count': 0, 'collision_backend': 'none'}
        return {
            'revision': int(getattr(scene, 'revision', 0) or 0),
            'obstacle_count': int(len(getattr(scene, 'obstacles', ()))),
            'collision_backend': str(getattr(scene, 'collision_backend', 'aabb')),
            'collision_level': getattr(getattr(scene, 'collision_level', None), 'value', str(getattr(scene, 'collision_level', 'aabb'))),
            'attached_objects': int(len(getattr(scene, 'attached_objects', ()))),
        }
