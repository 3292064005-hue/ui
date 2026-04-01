from __future__ import annotations

from time import perf_counter
from typing import Callable

import numpy as np

from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver
from robot_sim.core.kinematics.workspace import rough_reach_radius, target_is_certainly_outside_workspace
from robot_sim.core.math.linalg import (
    adaptive_damping_from_svd,
    clip_norm,
    damped_least_squares,
    weighted_damped_least_squares,
)
from robot_sim.core.math.so3 import rotation_error
from robot_sim.core.ik.validators import clip_to_joint_limits
from robot_sim.core.ik.nullspace import (
    can_use_nullspace,
    nullspace_projector,
    secondary_objective_gradient,
)
from robot_sim.core.ik.convergence import has_converged
from robot_sim.domain.enums import IKSolverMode
from robot_sim.domain.types import FloatArray
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig


class IterativeIKSolverBase:
    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()
        self._jac = JacobianSolver()

    def _inverse(self, J: FloatArray, config: IKConfig, *, damping_lambda: float, joint_weights: FloatArray | None = None) -> FloatArray:
        raise NotImplementedError

    def _joint_motion_weights(self, spec: RobotSpec, q: FloatArray, config: IKConfig) -> np.ndarray:
        weights = np.ones_like(q, dtype=float)
        for i, row in enumerate(spec.dh_rows):
            q_min = float(row.q_min)
            q_max = float(row.q_max)
            span = max(q_max - q_min, 1.0e-9)
            normalized = float((q[i] - q_min) / span)
            center_penalty = 1.0 + float(config.joint_limit_weight) * 0.25
            edge_boost = 1.0 + float(config.joint_limit_weight) * (4.0 * (normalized - 0.5) ** 2)
            weights[i] = max(center_penalty, edge_boost)
        return weights

    def _select_inverse(self, J_task: FloatArray, jac_condition: float, config: IKConfig, spec: RobotSpec, q: FloatArray) -> tuple[FloatArray, str, float]:
        damping_lambda = float(config.damping_lambda)
        effective_mode = config.mode.value
        if config.adaptive_damping:
            damping_lambda = adaptive_damping_from_svd(
                J_task,
                base_damping=config.damping_lambda,
                cond_threshold=config.singularity_cond_threshold,
                min_damping=config.min_damping_lambda,
                max_damping=config.max_damping_lambda,
            )
        if (
            config.fallback_to_dls_when_singular
            and config.mode is IKSolverMode.PINV
            and jac_condition >= config.singularity_cond_threshold
        ):
            effective_mode = IKSolverMode.DLS.value
            joint_weights = self._joint_motion_weights(spec, q, config) if config.use_weighted_least_squares else None
            if joint_weights is not None:
                return weighted_damped_least_squares(J_task, damping_lambda, joint_weights), effective_mode, damping_lambda
            return damped_least_squares(J_task, damping_lambda), effective_mode, damping_lambda

        joint_weights = self._joint_motion_weights(spec, q, config) if config.use_weighted_least_squares else None
        return self._inverse(J_task, config, damping_lambda=damping_lambda, joint_weights=joint_weights), effective_mode, damping_lambda

    def _classify_failure(
        self,
        spec: RobotSpec,
        target: Pose,
        config: IKConfig,
        *,
        pos_norm: float,
        ori_norm: float,
        cond: float,
        q: np.ndarray,
        best_q: np.ndarray,
        step_clipped_count: int,
    ) -> tuple[str, str]:
        if target_is_certainly_outside_workspace(spec, target, margin=config.pos_tol):
            return "workspace_precheck", "target outside rough workspace envelope"
        if pos_norm > max(config.pos_tol * 25.0, 5.0e-3):
            distance = float(np.linalg.norm(np.asarray(target.p, dtype=float) - np.asarray(spec.base_T[:3, 3], dtype=float)))
            if distance > rough_reach_radius(spec) * 0.98:
                return "position_unreachable", "position target appears outside practical reach"
        if (not config.position_only) and pos_norm <= max(config.pos_tol * 5.0, 1.0e-3) and ori_norm > max(config.ori_tol * 10.0, 5.0e-3):
            return "orientation_not_satisfied", "position matched but orientation target not satisfied"
        if np.isfinite(cond) and cond >= config.singularity_cond_threshold:
            return "singularity_stall", "solver stalled near singular configuration"
        mins = np.array([row.q_min for row in spec.dh_rows], dtype=float)
        maxs = np.array([row.q_max for row in spec.dh_rows], dtype=float)
        at_lower = np.isclose(q, mins, atol=1.0e-6)
        at_upper = np.isclose(q, maxs, atol=1.0e-6)
        if np.any(at_lower | at_upper):
            best_moved = float(np.linalg.norm(q - best_q))
            if best_moved <= max(config.max_step_norm * 0.5, 1.0e-6):
                return "joint_limit_blocked", "solver motion blocked by joint limits"
        if step_clipped_count >= max(int(config.max_iters * 0.5), 3):
            return "step_clipping_saturation", "solver repeatedly hit step clipping limits"
        return "max_iterations", "max iterations exceeded"

    def solve(
        self,
        spec: RobotSpec,
        target: Pose,
        q0: FloatArray,
        config: IKConfig,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[IKIterationLog], None] | None = None,
        *,
        attempt_idx: int = 0,
    ) -> IKResult:
        q = q0.astype(float).copy()
        logs: list[IKIterationLog] = []
        cancelled = cancel_flag or (lambda: False)
        t0 = perf_counter()
        best_q = q.copy()
        best_score = float("inf")
        step_clipped_count = 0

        if config.reachability_precheck and target_is_certainly_outside_workspace(spec, target, margin=config.pos_tol):
            return IKResult(
                False,
                q,
                tuple(logs),
                "target outside rough workspace envelope",
                stop_reason="workspace_precheck",
                best_q=best_q.copy(),
                diagnostics={
                    "attempt_idx": attempt_idx,
                    "workspace_radius": rough_reach_radius(spec),
                    "distance_to_target": float(np.linalg.norm(np.asarray(target.p, dtype=float) - np.asarray(spec.base_T[:3, 3], dtype=float))),
                },
            )

        for k in range(config.max_iters):
            if cancelled():
                return IKResult(
                    False,
                    q,
                    tuple(logs),
                    "cancelled",
                    stop_reason="cancelled",
                    best_q=best_q.copy(),
                    diagnostics={"attempt_idx": attempt_idx},
                )

            fk = self._fk.solve(spec, q)
            jac = self._jac.geometric(spec, q, fk=fk)

            pos_err = target.p - fk.ee_pose.p
            ori_err = rotation_error(target.R, fk.ee_pose.R)
            pos_norm = float(np.linalg.norm(pos_err))
            ori_norm = float(np.linalg.norm(ori_err))
            score = pos_norm + (0.0 if config.position_only else config.orientation_weight * ori_norm)
            if score < best_score:
                best_score = score
                best_q = q.copy()

            if config.position_only:
                err = pos_err
                J_task = jac.J[:3, :]
                ori_for_convergence = 0.0
            else:
                err = np.concatenate([pos_err, config.orientation_weight * ori_err])
                J_task = np.vstack([jac.J[:3, :], config.orientation_weight * jac.J[3:, :]])
                ori_for_convergence = ori_norm

            J_inv, effective_mode, damping_lambda = self._select_inverse(J_task, jac.condition_number, config, spec, q)
            dq_raw = J_inv @ err

            task_dim = J_task.shape[0]
            if config.enable_nullspace and can_use_nullspace(J_task.shape[1], task_dim):
                grad = secondary_objective_gradient(
                    spec,
                    q,
                    joint_limit_weight=config.joint_limit_weight,
                    manipulability_weight=config.manipulability_weight,
                )
                dq_raw += nullspace_projector(J_inv, J_task) @ grad

            dq = clip_norm(dq_raw, max_norm=config.max_step_norm)
            step_clipped = bool(np.linalg.norm(dq_raw) > np.linalg.norm(dq) + 1.0e-12)
            if step_clipped:
                step_clipped_count += 1
            dq_norm = float(np.linalg.norm(dq))
            log = IKIterationLog(
                iter_idx=k,
                pos_err_norm=pos_norm,
                ori_err_norm=ori_norm,
                cond_number=jac.condition_number,
                manipulability=jac.manipulability,
                dq_norm=dq_norm,
                elapsed_ms=(perf_counter() - t0) * 1000.0,
                effective_mode=effective_mode,
                attempt_idx=attempt_idx,
                damping_lambda=damping_lambda,
                score=score,
                step_clipped=step_clipped,
            )
            logs.append(log)
            if progress_cb is not None:
                progress_cb(log)

            if has_converged(pos_norm, ori_for_convergence, config.pos_tol, config.ori_tol):
                return IKResult(
                    True,
                    q.copy(),
                    tuple(logs),
                    "converged",
                    final_pos_err=pos_norm,
                    final_ori_err=ori_norm,
                    final_cond=jac.condition_number,
                    final_manipulability=jac.manipulability,
                    final_dq_norm=dq_norm,
                    elapsed_ms=log.elapsed_ms,
                    effective_mode=effective_mode,
                    stop_reason="converged",
                    best_q=best_q.copy(),
                    diagnostics={
                        "attempt_idx": attempt_idx,
                        "best_score": best_score,
                        "step_clipped_count": step_clipped_count,
                        "damping_lambda": damping_lambda,
                    },
                )

            q = clip_to_joint_limits(spec, q + config.step_scale * dq)

        final_fk = self._fk.solve(spec, q)
        final_jac = self._jac.geometric(spec, q, fk=final_fk)
        final_pos_err = target.p - final_fk.ee_pose.p
        final_ori_err_vec = rotation_error(target.R, final_fk.ee_pose.R)
        final_pos_norm = float(np.linalg.norm(final_pos_err))
        final_ori_norm = float(np.linalg.norm(final_ori_err_vec))
        stop_reason, message = self._classify_failure(
            spec,
            target,
            config,
            pos_norm=final_pos_norm,
            ori_norm=final_ori_norm,
            cond=final_jac.condition_number,
            q=q,
            best_q=best_q,
            step_clipped_count=step_clipped_count,
        )
        final_log = IKIterationLog(
            iter_idx=len(logs),
            pos_err_norm=final_pos_norm,
            ori_err_norm=final_ori_norm,
            cond_number=final_jac.condition_number,
            manipulability=final_jac.manipulability,
            dq_norm=0.0,
            elapsed_ms=(perf_counter() - t0) * 1000.0,
            effective_mode=(logs[-1].effective_mode if logs else config.mode.value),
            attempt_idx=attempt_idx,
            damping_lambda=(logs[-1].damping_lambda if logs else config.damping_lambda),
            score=final_pos_norm + (0.0 if config.position_only else config.orientation_weight * final_ori_norm),
            step_clipped=False,
        )
        logs.append(final_log)
        score = final_log.score
        if score < best_score:
            best_q = q.copy()

        return IKResult(
            False,
            q.copy(),
            tuple(logs),
            message,
            final_pos_err=final_pos_norm,
            final_ori_err=final_ori_norm,
            final_cond=final_jac.condition_number,
            final_manipulability=final_jac.manipulability,
            final_dq_norm=0.0,
            elapsed_ms=final_log.elapsed_ms,
            effective_mode=final_log.effective_mode,
            stop_reason=stop_reason,
            best_q=best_q.copy(),
            diagnostics={
                "attempt_idx": attempt_idx,
                "best_score": best_score,
                "step_clipped_count": step_clipped_count,
                "damping_lambda": final_log.damping_lambda,
            },
        )
