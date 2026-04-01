from __future__ import annotations

from collections.abc import Callable
import time

import numpy as np

from robot_sim.application.dto import IKRequest, TrajectoryRequest
from robot_sim.application.trajectory_metadata import build_planner_metadata
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.rotation.quaternion import from_matrix, to_matrix
from robot_sim.core.rotation.slerp import slerp
from robot_sim.core.trajectory.quintic import QuinticTrajectoryPlanner
from robot_sim.domain.errors import CancelledTaskError
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.trajectory_digest import ensure_trajectory_digest_metadata


class PlanCartesianTrajectoryUseCase:
    """Generate a Cartesian trajectory by sampling intermediate IK targets."""

    def __init__(self, ik_uc: RunIKUseCase) -> None:
        """Create the Cartesian trajectory use case.

        Args:
            ik_uc: IK use case used for each sampled Cartesian pose.

        Returns:
            None: Initializes planning dependencies only.

        Raises:
            ValueError: If ``ik_uc`` is not provided.
        """
        if ik_uc is None:
            raise ValueError('PlanCartesianTrajectoryUseCase requires an explicit IK use case')
        self._planner = QuinticTrajectoryPlanner()
        self._fk = ForwardKinematicsSolver()
        self._ik_uc = ik_uc

    def execute(
        self,
        req: TrajectoryRequest,
        *,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[float, str, dict[str, object] | None], None] | None = None,
        correlation_id: str | None = None,
    ) -> JointTrajectory:
        """Plan a Cartesian trajectory using sampled intermediate IK solves.

        Args:
            req: Cartesian trajectory request.
            cancel_flag: Optional cooperative cancellation callback.
            progress_cb: Optional progress callback receiving percent, message, and payload.
            correlation_id: Optional correlation identifier propagated into trajectory metadata.

        Returns:
            JointTrajectory: Planned sampled joint trajectory.

        Raises:
            ValueError: If required robot-spec or target-pose data is missing.
            CancelledTaskError: If execution is cancelled during sampling.
            RuntimeError: If a required IK sample cannot be solved.
        """
        if req.spec is None:
            raise ValueError('cartesian trajectory requires robot spec')
        if req.target_pose is None:
            raise ValueError('cartesian trajectory requires target pose')
        ik_config = self._cartesian_stage_config(req.ik_config or IKConfig())
        started = time.perf_counter()
        scalar_traj = self._planner.plan(np.array([0.0]), np.array([1.0]), req.duration, req.dt)
        alphas = np.clip(np.asarray(scalar_traj.q[:, 0], dtype=float), 0.0, 1.0)
        start_fk = self._fk.solve(req.spec, np.asarray(req.q_start, dtype=float))
        start_pose = start_fk.ee_pose
        q_prev = np.asarray(req.q_start, dtype=float).copy()
        qs: list[np.ndarray] = []
        ee_positions = [np.asarray(start_pose.p, dtype=float)]
        ee_rotations = [np.asarray(start_pose.R, dtype=float)]
        joint_positions = [np.asarray(start_fk.joint_positions, dtype=float)]
        planning_logs: list[dict[str, object]] = []
        q0_quat = from_matrix(start_pose.R)
        q1_quat = from_matrix(req.target_pose.R)
        rot_samples = slerp(q0_quat, q1_quat, alphas)
        total_samples = max(len(alphas), 1)
        sampling_started = time.perf_counter()
        fk_projection_ms = 0.0
        for idx, alpha in enumerate(alphas):
            if cancel_flag is not None and bool(cancel_flag()):
                raise CancelledTaskError('cartesian trajectory cancelled', metadata={'sample_idx': idx, 'total_samples': len(alphas)})
            p = (1.0 - alpha) * np.asarray(start_pose.p, dtype=float) + alpha * np.asarray(req.target_pose.p, dtype=float)
            pose_i = Pose(p=np.asarray(p, dtype=float), R=to_matrix(rot_samples[idx]))
            ik_req = IKRequest(spec=req.spec, target=pose_i, q0=q_prev.copy(), config=ik_config)
            result = self._ik_uc.execute(ik_req, cancel_flag=cancel_flag, progress_cb=None, correlation_id=correlation_id)
            entry = {
                'sample_idx': idx,
                'alpha': float(alpha),
                'success': bool(result.success),
                'stop_reason': result.stop_reason,
                'message': result.message,
                'final_pos_err': float(result.final_pos_err),
                'final_ori_err': float(result.final_ori_err),
                'correlation_id': str(correlation_id or ''),
            }
            if not result.success:
                if not self._cartesian_soft_accept(result, ik_config):
                    raise RuntimeError(f"Cartesian trajectory IK failed at sample {idx}/{len(alphas) - 1}: {result.message} [{result.stop_reason}]")
                q_prev = np.asarray(result.best_q if result.best_q is not None else result.q_sol, dtype=float).copy()
                entry['soft_accepted'] = True
                entry['accepted_q_source'] = 'best_q' if result.best_q is not None else 'q_sol'
            else:
                q_prev = np.asarray(result.q_sol, dtype=float).copy()
            planning_logs.append(entry)
            qs.append(q_prev)
            fk_started = time.perf_counter()
            fk = self._fk.solve(req.spec, q_prev)
            fk_projection_ms += (time.perf_counter() - fk_started) * 1000.0
            ee_positions.append(np.asarray(fk.ee_pose.p, dtype=float))
            ee_rotations.append(np.asarray(fk.ee_pose.R, dtype=float))
            joint_positions.append(np.asarray(fk.joint_positions, dtype=float))
            if progress_cb is not None:
                progress_cb(
                    float(((idx + 1) / total_samples) * 100.0),
                    f'cartesian samples solved {idx + 1}/{len(alphas)}',
                    {
                        'sample_idx': idx,
                        'total_samples': len(alphas),
                        'correlation_id': str(correlation_id or ''),
                    },
                )

        sampling_elapsed_ms = (time.perf_counter() - sampling_started) * 1000.0
        diff_started = time.perf_counter()
        q = np.asarray(qs, dtype=float)
        qd = np.gradient(q, scalar_traj.t, axis=0, edge_order=1)
        qdd = np.gradient(qd, scalar_traj.t, axis=0, edge_order=1)
        differentiation_elapsed_ms = (time.perf_counter() - diff_started) * 1000.0
        phase_timings_ms = {
            'sampling_ik': float(sampling_elapsed_ms),
            'fk_projection': float(fk_projection_ms),
            'differentiation': float(differentiation_elapsed_ms),
            'total': float((time.perf_counter() - started) * 1000.0),
        }
        metadata = build_planner_metadata(
            planner_id='cartesian_sampled',
            goal_source='cartesian_pose',
            cache_status='ready',
            mode=getattr(req.mode, 'value', req.mode),
            metadata={
                'planning_logs': planning_logs,
                'num_waypoints': int(len(alphas)),
                'has_cached_fk': True,
                'cached_fk_samples': int(q.shape[0]),
                'phase_timings_ms': phase_timings_ms,
            },
            correlation_id=correlation_id,
            has_complete_fk=True,
        )
        trajectory = JointTrajectory(
            t=np.asarray(scalar_traj.t, dtype=float),
            q=q,
            qd=np.asarray(qd, dtype=float),
            qdd=np.asarray(qdd, dtype=float),
            ee_positions=np.asarray(ee_positions[1:], dtype=float),
            joint_positions=np.asarray(joint_positions[1:], dtype=float),
            ee_rotations=np.asarray(ee_rotations[1:], dtype=float),
            metadata=metadata,
        )
        ensure_trajectory_digest_metadata(trajectory)
        return trajectory

    def _cartesian_soft_accept(self, result, config: IKConfig) -> bool:
        pos_limit = max(float(config.pos_tol) * 8.0, 3.0e-2)
        ori_limit = max(float(config.ori_tol) * 8.0, 5.0e-2)
        if float(result.final_pos_err) > pos_limit:
            return False
        if not config.position_only and float(result.final_ori_err) > ori_limit:
            return False
        return True

    def _cartesian_stage_config(self, config: IKConfig) -> IKConfig:
        return IKConfig(**{
            **config.__dict__,
            'max_iters': max(int(config.max_iters), 250),
            'retry_count': max(int(config.retry_count), 3),
            'adaptive_damping': True,
            'use_weighted_least_squares': True,
            'damping_lambda': max(float(config.damping_lambda), 0.08),
            'max_step_norm': max(float(config.max_step_norm), 0.4),
            'pos_tol': max(float(config.pos_tol), 2.0e-3),
            'ori_tol': max(float(config.ori_tol), 5.0e-3),
        })
