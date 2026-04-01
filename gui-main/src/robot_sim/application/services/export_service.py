from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from robot_sim.application.services.manifest_builder import ManifestBuilder, export_manifest_as_dict
from robot_sim.application.trajectory_metadata import resolve_planner_metadata
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.session_state import SessionState
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class ExportService:
    """Export service for trajectories, benchmark artifacts, and session state."""

    def __init__(self, export_dir: str | Path, version_catalog: VersionCatalog | None = None) -> None:
        """Create the export service.

        Args:
            export_dir: Destination directory for exported artifacts.
            version_catalog: Optional version catalog used for manifest metadata.

        Returns:
            None: Initializes export destinations only.

        Raises:
            OSError: If the export directory cannot be created.
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._versions = version_catalog or current_version_catalog()
        self._manifest_builder = ManifestBuilder(self._versions)

    def save_json(self, name: str, payload: dict) -> Path:
        path = self.export_dir / name
        with path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    def save_csv(self, name: str, array: np.ndarray, header: str = '') -> Path:
        path = self.export_dir / name
        np.savetxt(path, array, delimiter=',', header=header, comments='')
        return path

    def save_dict_csv(self, name: str, rows: list[dict[str, object]]) -> Path:
        path = self.export_dir / name
        with path.open('w', encoding='utf-8', newline='') as handle:
            if not rows:
                handle.write('')
                return path
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def build_manifest(
        self,
        *,
        robot_id: str | None = None,
        solver_id: str | None = None,
        planner_id: str | None = None,
        reproducibility_seed: int | None = None,
        files: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        schema_version: str | None = None,
        export_version: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, object]:
        """Build a structured export manifest for downstream consumers."""
        manifest = self._manifest_builder.build_manifest(
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
            reproducibility_seed=reproducibility_seed,
            files=files,
            metadata=metadata,
            schema_version=schema_version,
            export_version=export_version,
            correlation_id=correlation_id,
        )
        return export_manifest_as_dict(manifest)

    def save_trajectory(self, name: str, t: np.ndarray, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> Path:
        header_cols = ['t']
        header_cols += [f'q{i}' for i in range(q.shape[1])]
        header_cols += [f'qd{i}' for i in range(qd.shape[1])]
        header_cols += [f'qdd{i}' for i in range(qdd.shape[1])]
        merged = np.column_stack([t, q, qd, qdd])
        return self.save_csv(name, merged, header=','.join(header_cols))

    def save_trajectory_bundle(self, name: str, trajectory: JointTrajectory, *, robot_id: str | None = None, solver_id: str | None = None, planner_id: str | None = None) -> Path:
        stem = Path(name).stem
        path = self.export_dir / f'{stem}.npz'
        canonical = resolve_planner_metadata(trajectory.metadata)
        resolved_planner_id = str(planner_id or canonical['planner_id'] or '')
        manifest = self.build_manifest(
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=resolved_planner_id,
            files=[path.name],
            metadata={'kind': 'trajectory_bundle', 'cache_status': trajectory.cache_status, 'scene_revision': trajectory.scene_revision},
            correlation_id=str(trajectory.metadata.get('correlation_id', '') or ''),
        )
        payload: dict[str, object] = {
            't': np.asarray(trajectory.t, dtype=float),
            'q': np.asarray(trajectory.q, dtype=float),
            'qd': np.asarray(trajectory.qd, dtype=float),
            'qdd': np.asarray(trajectory.qdd, dtype=float),
            'manifest_json': json.dumps(manifest, ensure_ascii=False),
            'metadata_json': json.dumps(trajectory.metadata, ensure_ascii=False),
            'quality_json': json.dumps(trajectory.quality, ensure_ascii=False),
            'feasibility_json': json.dumps(trajectory.feasibility, ensure_ascii=False),
        }
        if trajectory.ee_positions is not None:
            payload['ee_positions'] = np.asarray(trajectory.ee_positions, dtype=float)
        if trajectory.joint_positions is not None:
            payload['joint_positions'] = np.asarray(trajectory.joint_positions, dtype=float)
        if trajectory.ee_rotations is not None:
            payload['ee_rotations'] = np.asarray(trajectory.ee_rotations, dtype=float)
        np.savez_compressed(path, **payload)
        return path

    def save_metrics(self, name: str, payload: dict) -> Path:
        return self.save_json(name, payload)

    def save_metrics_csv(self, name: str, payload: dict) -> Path:
        return self.save_dict_csv(name, [{'metric': key, 'value': value} for key, value in payload.items()])

    def save_benchmark_report(self, name: str, payload: dict) -> Path:
        return self.save_json(name, payload)

    def save_benchmark_cases_csv(self, name: str, report: BenchmarkReport) -> Path:
        return self.save_dict_csv(name, [dict(case) for case in report.cases])

    def save_session(self, name: str, state: SessionState) -> Path:
        task_snapshot = state.active_task_snapshot
        correlation_id = '' if task_snapshot is None else str(task_snapshot.correlation_id)
        planner_id = None
        if state.trajectory is not None:
            planner_id = resolve_planner_metadata(state.trajectory.metadata)['planner_id'] or None
        payload = {
            'manifest': self.build_manifest(
                robot_id=state.robot_spec.name if state.robot_spec is not None else None,
                solver_id=state.ik_result.effective_mode if state.ik_result is not None else None,
                planner_id=planner_id,
                files=[name],
                metadata={'kind': 'session'},
                schema_version=self._versions.session_schema_version,
                export_version=self._versions.session_schema_version,
                correlation_id=correlation_id,
            ),
            'robot_name': state.robot_spec.name if state.robot_spec is not None else None,
            'robot_label': state.robot_spec.label if state.robot_spec is not None else None,
            'robot_model_source': state.robot_spec.model_source if state.robot_spec is not None else None,
            'q_current': None if state.q_current is None else np.asarray(state.q_current, dtype=float).tolist(),
            'target_pose': None if state.target_pose is None else {'p': np.asarray(state.target_pose.p, dtype=float).tolist(), 'R': np.asarray(state.target_pose.R, dtype=float).tolist(), 'frame': getattr(state.target_pose.frame, 'value', str(state.target_pose.frame))},
            'ik': None if state.ik_result is None else {
                'success': state.ik_result.success,
                'message': state.ik_result.message,
                'iterations': len(state.ik_result.logs),
                'final_pos_err': float(state.ik_result.final_pos_err),
                'final_ori_err': float(state.ik_result.final_ori_err),
                'stop_reason': state.ik_result.stop_reason,
                'restarts_used': int(state.ik_result.restarts_used),
                'diagnostics': dict(state.ik_result.diagnostics),
            },
            'trajectory': None if state.trajectory is None else {
                'num_samples': int(state.trajectory.t.shape[0]),
                'dof': int(state.trajectory.q.shape[1]),
                'cached_fk': bool(state.trajectory.ee_positions is not None and state.trajectory.joint_positions is not None),
                'cache_status': state.trajectory.cache_status,
                'metadata': dict(state.trajectory.metadata),
                'quality': dict(state.trajectory.quality),
                'feasibility': dict(state.trajectory.feasibility),
            },
            'benchmark_report': None if state.benchmark_report is None else {
                'robot': state.benchmark_report.robot,
                'num_cases': int(state.benchmark_report.num_cases),
                'success_rate': float(state.benchmark_report.success_rate),
                'aggregate': dict(state.benchmark_report.aggregate),
                'metadata': dict(state.benchmark_report.metadata),
                'comparison': dict(state.benchmark_report.comparison),
            },
            'playback': {
                'frame_idx': int(state.playback.frame_idx),
                'total_frames': int(state.playback.total_frames),
                'speed_multiplier': float(state.playback.speed_multiplier),
                'loop_enabled': bool(state.playback.loop_enabled),
            },
            'planning_scene': None if state.planning_scene is None else {
                'revision': int(getattr(state.planning_scene, 'revision', 0)),
                'collision_level': getattr(getattr(state.planning_scene, 'collision_level', None), 'value', str(getattr(state.planning_scene, 'collision_level', 'aabb'))),
                'collision_backend': str(getattr(state.planning_scene, 'collision_backend', 'aabb')),
                'obstacle_ids': list(getattr(state.planning_scene, 'obstacle_ids', ())),
                'attached_object_ids': [obj.object_id for obj in getattr(state.planning_scene, 'attached_objects', ())],
                'summary': dict(getattr(state, 'scene_summary', {}) or {}),
            },
            'app_state': getattr(state.app_state, 'value', str(state.app_state)),
            'active_task_id': state.active_task_id,
            'active_task_kind': state.active_task_kind,
            'warnings': list(state.warnings),
            'last_error': state.last_error,
            'last_error_payload': dict(state.last_error_payload),
            'last_error_code': state.last_error_code,
            'last_error_title': state.last_error_title,
            'last_error_severity': state.last_error_severity,
            'last_error_hint': state.last_error_hint,
            'active_task_snapshot': None if task_snapshot is None else {
                'task_id': task_snapshot.task_id,
                'task_kind': task_snapshot.task_kind,
                'task_state': task_snapshot.task_state.value,
                'progress_stage': task_snapshot.progress_stage,
                'progress_percent': float(task_snapshot.progress_percent),
                'message': task_snapshot.message,
                'correlation_id': task_snapshot.correlation_id,
                'started_at': None if task_snapshot.started_at is None else task_snapshot.started_at.isoformat(),
                'finished_at': None if task_snapshot.finished_at is None else task_snapshot.finished_at.isoformat(),
                'stop_reason': task_snapshot.stop_reason,
            },
            'scene_revision': int(state.scene_revision),
        }
        return self.save_json(name, payload)
